"""Tests for the Beidou upstream API client."""

from typing import Any

import httpx
import pytest

from app.services.beidou.client import BeidouClient, BeidouRequestError

pytestmark = pytest.mark.unit


class FakeResponse:
    """Minimal httpx response double for Beidou client tests."""

    def __init__(self, status_code: int, payload: Any, *, json_error: Exception | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self) -> Any:
        """Return configured JSON payload or raise configured parse error."""
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeAsyncClient:
    """Async context manager that records POST calls."""

    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.posts: list[tuple[str, dict[str, str]]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
        self.posts.append((url, json))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


async def test_login_success_returns_session_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful upstream login returns the session UUID and fixed endpoint is used."""
    fake = FakeAsyncClient(
        FakeResponse(200, {"ResponseCode": "200", "SessionUUID": "550e8400-e29b-41d4-a716-446655440000"})
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)

    result = await BeidouClient("https://example.test/API", timeout_seconds=1).login("fake_user", "FakePassword123!")

    assert result.session_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert fake.posts == [
        (
            "https://example.test/API/UserLogin/doLogin.php",
            {"Username": "fake_user", "Password": "FakePassword123!"},
        )
    ]


async def test_login_rejects_success_without_valid_session_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    """ResponseCode 200 without a UUID session is treated as a bad upstream response."""
    fake = FakeAsyncClient(FakeResponse(200, {"ResponseCode": "200", "SessionUUID": ""}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)

    with pytest.raises(BeidouRequestError) as error:
        await BeidouClient("https://example.test/API", timeout_seconds=1).login("fake_user", "FakePassword123!")

    assert error.value.error_code == "beidou_bad_response"
    assert not error.value.retryable


async def test_login_maps_invalid_credentials_to_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Business authentication failures are not retryable."""
    fake = FakeAsyncClient(FakeResponse(200, {"ResponseCode": "400111", "ResponseMsg": "账号名称或账号密码输入错误"}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)

    with pytest.raises(BeidouRequestError) as error:
        await BeidouClient("https://example.test/API", timeout_seconds=1).login("fake_user", "FakePassword123!")

    assert error.value.error_code == "beidou_invalid_credentials"
    assert not error.value.retryable


async def test_login_timeout_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network timeouts are reported as retryable upstream failures."""
    fake = FakeAsyncClient(httpx.TimeoutException("timeout"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake)

    with pytest.raises(BeidouRequestError) as error:
        await BeidouClient("https://example.test/API", timeout_seconds=1).login("fake_user", "FakePassword123!")

    assert error.value.error_code == "beidou_timeout"
    assert error.value.retryable
