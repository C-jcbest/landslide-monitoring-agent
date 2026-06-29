"""Beidou station query service."""

import time
from typing import (
    Any,
    Protocol,
)

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import logger
from app.schemas.beidou_station import (
    BeidouPageInfo,
    BeidouSession,
    BeidouStation,
    BeidouStationGroup,
    StationCandidate,
    station_to_candidate,
)

STATION_GROUP_PATH = "Station/getStationGroupListInfo.php"
STATION_LIST_PATH = "Station/getStationListInfo.php"


class BeidouSessionProvider(Protocol):
    """Protocol for resolving the current user's Beidou upstream session."""

    async def get_session(self, user_id: str) -> BeidouSession | None:
        """Return a usable Beidou session for a local user, if configured."""


class UnconfiguredBeidouSessionProvider:
    """Default provider used before the credential-binding branch is merged."""

    async def get_session(self, user_id: str) -> BeidouSession | None:
        """Return no session until credential binding is wired in."""
        logger.info("beidou_session_provider_unconfigured", user_id=user_id)
        return None


class BeidouStationError(Exception):
    """Structured Beidou station request failure."""

    def __init__(self, error_code: str, message: str, *, retryable: bool) -> None:
        """Initialize a structured Beidou station error."""
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.retryable = retryable


def _is_retryable_beidou_station_error(exception: BaseException) -> bool:
    return isinstance(exception, BeidouStationError) and exception.retryable


class BeidouStationClient:
    """Async client for Beidou station group and station list APIs."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize the station client with fixed upstream configuration."""
        self.base_url = (base_url or settings.BEIDOU_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.BEIDOU_API_TIMEOUT_SECONDS
        self.transport = transport

    async def get_station_groups(self, session: BeidouSession) -> list[BeidouStationGroup]:
        """Return station groups accessible to the current Beidou session."""
        logger.info("beidou_station_groups_requested")
        payload = await self._post_json(STATION_GROUP_PATH, {"SessionUUID": session.session_uuid})
        groups = payload.get("StationGroupList")
        if not isinstance(groups, list):
            raise BeidouStationError("beidou_bad_response", "北斗平台返回分组格式异常。", retryable=False)
        return [_parse_group(item) for item in groups if isinstance(item, dict)]

    async def get_stations(
        self,
        session: BeidouSession,
        *,
        station_group_uuid: str | None = None,
        station_uuid: str | None = None,
        page_size: int | None = None,
    ) -> list[BeidouStation]:
        """Return stations accessible to the current Beidou session."""
        logger.info(
            "beidou_station_list_requested",
            has_station_group=station_group_uuid is not None,
            has_station_uuid=station_uuid is not None,
        )
        request_page_size = page_size or settings.BEIDOU_STATION_PAGE_SIZE
        request_payload: dict[str, Any] = {
            "SessionUUID": session.session_uuid,
            "PageInfo": {
                "PageFlag": "StationNameAsc",
                "PageNumber": 1,
                "PageSize": request_page_size,
            },
        }
        if station_group_uuid:
            request_payload["StationGroupUUID"] = station_group_uuid
        if station_uuid:
            request_payload["StationUUID"] = station_uuid

        payload = await self._post_json(STATION_LIST_PATH, request_payload)
        stations = payload.get("StationList")
        if not isinstance(stations, list):
            raise BeidouStationError("beidou_bad_response", "北斗平台返回站点列表格式异常。", retryable=False)
        return [_parse_station(item) for item in stations if isinstance(item, dict)]

    async def get_station_detail(self, session: BeidouSession, station_uuid: str) -> BeidouStation:
        """Return exactly one station detail by StationUUID."""
        logger.info("beidou_station_detail_requested", station_uuid=station_uuid)
        stations = await self.get_stations(session, station_uuid=station_uuid, page_size=1)
        if not stations:
            raise BeidouStationError("station_not_found", "未找到该站点，或当前用户无权访问。", retryable=False)
        if len(stations) > 1:
            raise BeidouStationError("station_ambiguous", "北斗平台返回了多个站点，无法唯一确认。", retryable=False)
        return stations[0]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable_beidou_station_error),
        reraise=True,
    )
    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self._endpoint(path)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.post(endpoint, json=payload)
        except httpx.TimeoutException as e:
            logger.warning("beidou_station_request_failed", endpoint=path, error_code="beidou_timeout")
            raise BeidouStationError("beidou_timeout", "北斗平台请求超时，请稍后重试。", retryable=True) from e
        except httpx.RequestError as e:
            logger.warning("beidou_station_request_failed", endpoint=path, error_code="beidou_unavailable")
            raise BeidouStationError("beidou_unavailable", "北斗平台暂时不可用，请稍后重试。", retryable=True) from e

        duration_ms = round((time.monotonic() - started) * 1000, 2)
        logger.info(
            "beidou_station_request_finished",
            endpoint=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        if response.status_code >= 500:
            raise BeidouStationError("beidou_unavailable", "北斗平台暂时不可用，请稍后重试。", retryable=True)
        if response.status_code >= 400:
            raise BeidouStationError("beidou_request_rejected", "北斗平台拒绝了本次站点查询。", retryable=False)

        try:
            body = response.json()
        except ValueError as e:
            raise BeidouStationError("beidou_bad_response", "北斗平台返回格式异常。", retryable=False) from e
        if not isinstance(body, dict):
            raise BeidouStationError("beidou_bad_response", "北斗平台返回格式异常。", retryable=False)

        response_code = body.get("ResponseCode")
        if response_code != "200":
            raise _error_from_response_code(str(response_code), str(body.get("ResponseMsg") or "北斗平台请求失败。"))
        return body

    def _endpoint(self, path: str) -> str:
        if path not in {STATION_GROUP_PATH, STATION_LIST_PATH}:
            raise BeidouStationError("invalid_input", "不允许访问未配置的北斗接口。", retryable=False)
        return f"{self.base_url}/{path}"


class BeidouStationService:
    """Application service for Beidou station facts and LLM-safe candidates."""

    def __init__(self, client: BeidouStationClient) -> None:
        """Initialize the station service."""
        self.client = client

    async def get_station_groups(self, session: BeidouSession) -> list[BeidouStationGroup]:
        """Return station groups for the current user session."""
        return await self.client.get_station_groups(session)

    async def get_stations(self, session: BeidouSession, station_group_uuid: str | None = None) -> list[BeidouStation]:
        """Return stations for the current user session."""
        return await self.client.get_stations(session, station_group_uuid=station_group_uuid)

    async def get_station_detail(self, session: BeidouSession, station_uuid: str) -> BeidouStation:
        """Return station detail for the current user session."""
        return await self.client.get_station_detail(session, station_uuid)

    async def get_station_candidates(self, session: BeidouSession) -> list[StationCandidate]:
        """Return LLM-safe station candidates for the current user session."""
        stations = await self.client.get_stations(session)
        return [station_to_candidate(station) for station in stations[: settings.BEIDOU_STATION_CANDIDATE_LIMIT]]


def create_beidou_station_service() -> BeidouStationService:
    """Create the production Beidou station service."""
    return BeidouStationService(BeidouStationClient())


def _error_from_response_code(response_code: str, response_msg: str) -> BeidouStationError:
    mapping = {
        "400000": ("beidou_permission_denied", False),
        "400100": ("beidou_bad_session", False),
        "400101": ("beidou_session_invalid", False),
        "100001": ("beidou_unavailable", True),
        "100003": ("beidou_unavailable", True),
    }
    error_code, retryable = mapping.get(response_code, ("beidou_request_failed", False))
    return BeidouStationError(error_code, response_msg, retryable=retryable)


def _parse_group(item: dict[str, Any]) -> BeidouStationGroup:
    return BeidouStationGroup(
        station_group_uuid=str(item.get("StationGroupUUID") or ""),
        station_group_name=str(item.get("StationGroupName") or ""),
        station_count=int(item.get("StationCount") or 0),
        station_group_desc=_optional_str(item.get("StationGroupDesc")),
    )


def _parse_station(item: dict[str, Any]) -> BeidouStation:
    station_uuid = str(item.get("StationUUID") or "")
    station_name = str(item.get("StationName") or "")
    if not station_uuid or not station_name:
        raise BeidouStationError("beidou_bad_response", "北斗平台返回站点字段缺失。", retryable=False)
    return BeidouStation(
        station_group_uuid=_optional_str(item.get("StationGroupUUID")),
        station_group_name=_optional_str(item.get("StationGroupName")),
        station_uuid=station_uuid,
        device_uuid=_optional_str(item.get("DeviceUUID")),
        station_name=station_name,
        station_n0=_optional_str(item.get("StationN0")),
        station_e0=_optional_str(item.get("StationE0")),
        station_u0=_optional_str(item.get("StationU0")),
        station_type=_optional_int(item.get("StationType")),
        station_location=_optional_str(item.get("StationLocation")),
        station_status=_optional_int(item.get("StationStatus")),
        station_desc=_optional_str(item.get("StationDesc")),
        base_station_uuid=_optional_str(item.get("BaseStationUUID")),
        base_station_name=_optional_str(item.get("BaseStationName")),
        latitude=_optional_str(item.get("Latitude")),
        longitude=_optional_str(item.get("Longitude")),
        altitude=_optional_str(item.get("Altitude")),
    )


def _parse_page_info(item: dict[str, Any] | None) -> BeidouPageInfo:
    item = item or {}
    return BeidouPageInfo(
        page_flag=_optional_str(item.get("PageFlag")),
        page_number=_optional_int(item.get("PageNumber")),
        page_size=_optional_int(item.get("PageSize")),
        total_number=_optional_int(item.get("TotalNumber")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
