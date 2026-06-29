"""API tests for Beidou credential endpoints."""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.api.v1 import beidou
from app.schemas.beidou import BeidouCredentialStatusResponse
from app.services.beidou.client import BeidouRequestError

pytestmark = pytest.mark.api


class FakeCredentialService:
    """Configurable service double for route tests."""

    def __init__(self) -> None:
        self.status = BeidouCredentialStatusResponse(bound=False)
        self.bound_args: tuple[int, str, str] | None = None
        self.unbound_user_id: int | None = None
        self.error: Exception | None = None

    async def get_status(self, user_id: int) -> BeidouCredentialStatusResponse:
        if self.error:
            raise self.error
        return self.status

    async def bind_or_update(self, user_id: int, username: str, password: str) -> BeidouCredentialStatusResponse:
        if self.error:
            raise self.error
        self.bound_args = (user_id, username, password)
        return self.status

    async def unbind(self, user_id: int) -> BeidouCredentialStatusResponse:
        if self.error:
            raise self.error
        self.unbound_user_id = user_id
        return BeidouCredentialStatusResponse(bound=False)


async def test_status_returns_unbound_without_sensitive_fields(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Status endpoint returns the safe unbound contract."""
    service = FakeCredentialService()
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.get("/api/v1/beidou/credentials/status")

    assert response.status_code == 200
    body = response.json()
    assert body["bound"] is False
    assert "password" not in body
    assert "encrypted_password" not in body
    assert "session_uuid" not in body


async def test_status_returns_bound_username_without_session_uuid(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bound status includes username but never exposes upstream session material."""
    service = FakeCredentialService()
    service.status = BeidouCredentialStatusResponse(
        bound=True,
        username="fake_beidou_user",
        last_verified_at=datetime(2026, 6, 29, 8, 0, tzinfo=UTC),
        session_expires_at=datetime(2026, 6, 29, 16, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.get("/api/v1/beidou/credentials/status")

    assert response.status_code == 200
    body = response.json()
    assert body["bound"] is True
    assert body["username"] == "fake_beidou_user"
    assert all("session_uuid" not in key for key in body)


async def test_bind_delegates_authenticated_user_and_secret(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """PUT credentials delegates the current user and request secret to the service."""
    service = FakeCredentialService()
    service.status = BeidouCredentialStatusResponse(bound=True, username="fake_beidou_user")
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.put(
        "/api/v1/beidou/credentials",
        json={"username": "fake_beidou_user", "password": "FakePassword123!"},
    )

    assert response.status_code == 200
    assert response.json()["bound"] is True
    assert service.bound_args == (101, "fake_beidou_user", "FakePassword123!")


async def test_bind_maps_upstream_auth_failure_to_client_error(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Upstream authentication failures are returned as understandable client errors."""
    service = FakeCredentialService()
    service.error = BeidouRequestError("beidou_invalid_credentials", "账号名称或账号密码输入错误", retryable=False)
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.put(
        "/api/v1/beidou/credentials",
        json={"username": "fake_beidou_user", "password": "FakePassword123!"},
    )

    assert response.status_code == 401
    assert "账号" in response.json()["detail"]


async def test_unbind_returns_unbound_status(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """DELETE credentials is idempotent and user-scoped."""
    service = FakeCredentialService()
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.delete("/api/v1/beidou/credentials")

    assert response.status_code == 200
    assert response.json() == {
        "bound": False,
        "username": None,
        "last_verified_at": None,
        "session_expires_at": None,
    }
    assert service.unbound_user_id == 101


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "", "password": "FakePassword123!"},
        {"username": "fake_beidou_user", "password": "short"},
    ],
)
async def test_bind_rejects_invalid_payload_before_service_call(
    client, monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    """Invalid payloads fail validation before the service is invoked."""
    service = FakeCredentialService()
    monkeypatch.setattr(beidou, "credential_service", service)

    response = await client.put("/api/v1/beidou/credentials", json=payload)

    assert response.status_code == 422
    assert service.bound_args is None
