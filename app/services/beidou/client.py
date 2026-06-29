"""Async client for the Beidou monitoring platform API."""

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import logger


@dataclass(frozen=True)
class BeidouLoginResult:
    """Successful Beidou login result."""

    session_uuid: str


class BeidouRequestError(Exception):
    """Structured Beidou upstream request failure."""

    def __init__(self, error_code: str, message: str, *, retryable: bool) -> None:
        """Initialize a structured upstream error."""
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.retryable = retryable


def _is_retryable_beidou_error(exception: BaseException) -> bool:
    return isinstance(exception, BeidouRequestError) and exception.retryable


class BeidouClient:
    """Restricted client for fixed Beidou API endpoints."""

    def __init__(self, base_url: str, *, timeout_seconds: float) -> None:
        """Initialize the client with a fixed API base URL."""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable_beidou_error),
        reraise=True,
    )
    async def login(self, username: str, password: str) -> BeidouLoginResult:
        """Verify Beidou credentials and return a session UUID."""
        endpoint = f"{self.base_url}/UserLogin/doLogin.php"
        started = time.monotonic()
        logger.info("beidou_login_verification_started", beidou_username=username)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(endpoint, json={"Username": username, "Password": password})
        except httpx.TimeoutException as e:
            logger.warning("beidou_login_verification_failed", error_code="beidou_timeout")
            raise BeidouRequestError("beidou_timeout", "北斗平台请求超时，请稍后重试。", retryable=True) from e
        except httpx.RequestError as e:
            logger.warning("beidou_login_verification_failed", error_code="beidou_unavailable")
            raise BeidouRequestError("beidou_unavailable", "北斗平台暂时不可用，请稍后重试。", retryable=True) from e

        duration_ms = round((time.monotonic() - started) * 1000, 2)
        logger.info(
            "beidou_login_verification_finished",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        if response.status_code >= 500:
            raise BeidouRequestError("beidou_unavailable", "北斗平台暂时不可用，请稍后重试。", retryable=True)
        if response.status_code >= 400:
            raise BeidouRequestError("beidou_request_rejected", "北斗平台拒绝了本次认证请求。", retryable=False)

        try:
            payload = response.json()
        except ValueError as e:
            raise BeidouRequestError("beidou_bad_response", "北斗平台返回格式异常。", retryable=False) from e
        if not isinstance(payload, dict):
            raise BeidouRequestError("beidou_bad_response", "北斗平台返回格式异常。", retryable=False)

        return _parse_login_payload(payload)


def _parse_login_payload(payload: dict[str, Any]) -> BeidouLoginResult:
    response_code = str(payload.get("ResponseCode", ""))
    response_msg = str(payload.get("ResponseMsg", "北斗平台认证失败。"))

    if response_code == "200":
        session_uuid = payload.get("SessionUUID")
        if not isinstance(session_uuid, str) or not _is_uuid(session_uuid):
            raise BeidouRequestError("beidou_bad_response", "北斗平台返回格式异常。", retryable=False)
        return BeidouLoginResult(session_uuid=session_uuid)

    error_code = {
        "400000": "beidou_permission_denied",
        "400110": "beidou_invalid_account_format",
        "400111": "beidou_invalid_credentials",
        "400113": "beidou_password_expired",
        "400114": "beidou_account_disabled",
        "400115": "beidou_invalid_password_format",
    }.get(response_code, "beidou_auth_failed")
    raise BeidouRequestError(error_code, response_msg, retryable=False)


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True
