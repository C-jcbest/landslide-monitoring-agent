"""Tests for Beidou station query service."""

from typing import Any

import httpx
import pytest

from app.schemas.beidou_station import BeidouSession
from app.services.beidou.stations import (
    BeidouStationClient,
    BeidouStationError,
    BeidouStationService,
)

pytestmark = pytest.mark.unit

SESSION_UUID = "00000000-0000-4000-8000-000000000000"
GROUP_UUID = "11111111-1111-4111-8111-111111111111"
STATION_UUID = "22222222-2222-4222-8222-222222222222"


def _transport(payload: dict[str, Any], status_code: int = 200) -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload, request=request)

    return httpx.MockTransport(handler)


def _station_payload() -> dict[str, Any]:
    return {
        "ResponseCode": "200",
        "ResponseMsg": "操作成功",
        "PageInfo": {
            "PageFlag": "StationNameAsc",
            "PageNumber": 1,
            "PageSize": 10,
            "TotalNumber": 1,
        },
        "StationList": [
            {
                "StationGroupUUID": GROUP_UUID,
                "StationGroupName": "北坡监测组",
                "StationUUID": STATION_UUID,
                "DeviceUUID": "DEV-BP-001",
                "StationName": "北坡 GNSS 01",
                "StationN0": "4421290.4231",
                "StationE0": "198942.5203",
                "StationU0": "17.2676",
                "StationType": 3,
                "StationLocation": "北坡一号滑坡体",
                "StationStatus": 10,
                "StationDesc": "北坡 GNSS 监测点",
                "BaseStationUUID": "33333333-3333-4333-8333-333333333333",
                "BaseStationName": "北坡基准站",
                "Latitude": "39.759630522",
                "Longitude": "116.986252277",
                "Altitude": "44.2287",
            }
        ],
    }


async def test_station_groups_are_loaded_from_fixed_endpoint() -> None:
    """Group list requests use the fixed station-group endpoint and normalize response data."""
    seen: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path, "body": request.read().decode()})
        return httpx.Response(
            200,
            json={
                "ResponseCode": "200",
                "ResponseMsg": "操作成功",
                "StationGroupList": [
                    {
                        "StationGroupUUID": GROUP_UUID,
                        "StationGroupName": "北坡监测组",
                        "StationCount": 2,
                        "StationGroupDesc": "北坡 GNSS 监测点分组",
                    }
                ],
            },
            request=request,
        )

    client = BeidouStationClient(base_url="https://beidou.example/API", transport=httpx.MockTransport(handler))
    groups = await client.get_station_groups(BeidouSession(session_uuid=SESSION_UUID))

    assert seen[0]["path"] == "/API/Station/getStationGroupListInfo.php"
    assert "SessionUUID" in seen[0]["body"]
    assert groups[0].station_group_uuid == GROUP_UUID
    assert groups[0].station_count == 2


async def test_station_detail_is_loaded_with_station_uuid() -> None:
    """Station detail is read through the station-list endpoint with StationUUID."""
    seen: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path, "body": request.read().decode()})
        return httpx.Response(200, json=_station_payload(), request=request)

    client = BeidouStationClient(base_url="https://beidou.example/API", transport=httpx.MockTransport(handler))
    detail = await client.get_station_detail(BeidouSession(session_uuid=SESSION_UUID), STATION_UUID)

    assert seen[0]["path"] == "/API/Station/getStationListInfo.php"
    assert STATION_UUID in seen[0]["body"]
    assert detail.station_uuid == STATION_UUID
    assert detail.station_name == "北坡 GNSS 01"
    assert detail.device_uuid == "DEV-BP-001"


async def test_station_detail_rejects_ambiguous_upstream_response() -> None:
    """A StationUUID detail query must not accept multiple upstream station records."""
    payload = _station_payload()
    payload["StationList"] = [payload["StationList"][0], {**payload["StationList"][0], "StationUUID": GROUP_UUID}]
    client = BeidouStationClient(base_url="https://beidou.example/API", transport=_transport(payload))

    with pytest.raises(BeidouStationError) as error:
        await client.get_station_detail(BeidouSession(session_uuid=SESSION_UUID), STATION_UUID)

    assert error.value.error_code == "station_ambiguous"
    assert not error.value.retryable


async def test_upstream_permission_denied_is_mapped_to_structured_error() -> None:
    """Upstream permission failures are non-retryable structured errors."""
    client = BeidouStationClient(
        base_url="https://beidou.example/API",
        transport=_transport({"ResponseCode": "400000", "ResponseMsg": "权限不足"}),
    )

    with pytest.raises(BeidouStationError) as error:
        await client.get_stations(BeidouSession(session_uuid=SESSION_UUID))

    assert error.value.error_code == "beidou_permission_denied"
    assert not error.value.retryable


async def test_candidate_projection_excludes_session_uuid_and_raw_response() -> None:
    """Candidate data sent to the LLM is deliberately narrow and does not leak session credentials."""
    client = BeidouStationClient(base_url="https://beidou.example/API", transport=_transport(_station_payload()))
    service = BeidouStationService(client)
    candidates = await service.get_station_candidates(BeidouSession(session_uuid=SESSION_UUID))

    projected = candidates[0].model_dump()

    assert projected == {
        "station_uuid": STATION_UUID,
        "station_name": "北坡 GNSS 01",
        "station_group_name": "北坡监测组",
        "device_uuid": "DEV-BP-001",
        "station_type": 3,
        "station_status": 10,
        "station_location": "北坡一号滑坡体",
        "base_station_name": "北坡基准站",
    }
    assert SESSION_UUID not in str(projected)
