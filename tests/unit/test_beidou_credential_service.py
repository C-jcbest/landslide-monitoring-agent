"""Tests for Beidou credential binding service."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.beidou_credential import BeidouCredential
from app.services.beidou.client import BeidouLoginResult, BeidouRequestError
from app.services.beidou.credentials import BeidouCredentialRepository, BeidouCredentialService
from app.services.beidou.stations import CredentialBeidouSessionProvider

pytestmark = pytest.mark.unit


class FakeRepository(BeidouCredentialRepository):
    """In-memory repository double."""

    def __init__(self, existing: BeidouCredential | None = None) -> None:
        self.credential = existing
        self.saved: BeidouCredential | None = None
        self.deleted_user_id: int | None = None

    async def get_by_user_id(self, user_id: int) -> BeidouCredential | None:
        if self.credential and self.credential.user_id == user_id:
            return self.credential
        return None

    async def upsert(self, credential: BeidouCredential) -> BeidouCredential:
        self.credential = credential
        self.saved = credential
        return credential

    async def delete_by_user_id(self, user_id: int) -> bool:
        self.deleted_user_id = user_id
        existed = self.credential is not None and self.credential.user_id == user_id
        if existed:
            self.credential = None
        return existed


class FakeClient:
    """Beidou client double."""

    def __init__(self, result: BeidouLoginResult | BeidouRequestError) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    async def login(self, username: str, password: str) -> BeidouLoginResult:
        self.calls.append((username, password))
        if isinstance(self.result, BeidouRequestError):
            raise self.result
        return self.result


class FakeCrypto:
    """Deterministic crypto double."""

    def encrypt(self, value: str) -> str:
        return f"encrypted:{value}"

    def decrypt(self, value: str) -> str:
        return value.removeprefix("encrypted:")


def fixed_now() -> datetime:
    """Return deterministic UTC time."""
    return datetime(2026, 6, 29, 8, 0, 0, tzinfo=UTC)


async def test_status_returns_unbound_when_credential_is_missing() -> None:
    """Missing credential returns a safe unbound status."""
    service = BeidouCredentialService(
        FakeRepository(), FakeClient(BeidouLoginResult("unused")), FakeCrypto(), now=fixed_now
    )

    status = await service.get_status(user_id=101)

    assert not status.bound
    assert status.username is None


async def test_status_does_not_require_crypto_configuration() -> None:
    """Status checks do not need to initialize encryption configuration."""
    service = BeidouCredentialService(FakeRepository(), FakeClient(BeidouLoginResult("unused")), now=fixed_now)

    status = await service.get_status(user_id=101)

    assert not status.bound


async def test_bind_verifies_upstream_then_saves_encrypted_values() -> None:
    """A successful bind verifies upstream before storing encrypted secrets."""
    repository = FakeRepository()
    client = FakeClient(BeidouLoginResult("550e8400-e29b-41d4-a716-446655440000"))
    service = BeidouCredentialService(repository, client, FakeCrypto(), now=fixed_now, session_ttl_seconds=28800)

    status = await service.bind_or_update(user_id=101, username="fake_beidou_user", password="FakePassword123!")

    assert status.bound
    assert status.username == "fake_beidou_user"
    assert client.calls == [("fake_beidou_user", "FakePassword123!")]
    assert repository.saved is not None
    assert repository.saved.encrypted_password == "encrypted:FakePassword123!"
    assert repository.saved.session_uuid_encrypted == "encrypted:550e8400-e29b-41d4-a716-446655440000"
    assert repository.saved.session_expires_at is not None
    assert repository.saved.session_expires_at.hour == 16


async def test_session_provider_returns_bound_unexpired_session() -> None:
    """Agent session provider resolves the encrypted session saved by credential binding."""
    existing = BeidouCredential(
        user_id=101,
        beidou_username="fake_beidou_user",
        encrypted_password="encrypted:FakePassword123!",
        session_uuid_encrypted="encrypted:550e8400-e29b-41d4-a716-446655440000",
        session_expires_at=fixed_now() + timedelta(hours=1),
        last_verified_at=fixed_now(),
        updated_at=fixed_now(),
    )
    client = FakeClient(BeidouLoginResult("unused"))
    provider = CredentialBeidouSessionProvider(FakeRepository(existing), client, FakeCrypto(), now=fixed_now)

    session = await provider.get_session("101")

    assert session is not None
    assert session.session_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert client.calls == []


async def test_session_provider_refreshes_expired_bound_session() -> None:
    """Expired stored sessions are refreshed using the encrypted bound password."""
    existing = BeidouCredential(
        user_id=101,
        beidou_username="fake_beidou_user",
        encrypted_password="encrypted:FakePassword123!",
        session_uuid_encrypted="encrypted:old-session",
        session_expires_at=fixed_now() - timedelta(minutes=1),
        last_verified_at=fixed_now(),
        updated_at=fixed_now(),
    )
    repository = FakeRepository(existing)
    client = FakeClient(BeidouLoginResult("550e8400-e29b-41d4-a716-446655440000"))
    provider = CredentialBeidouSessionProvider(
        repository,
        client,
        FakeCrypto(),
        now=fixed_now,
        session_ttl_seconds=28800,
    )

    session = await provider.get_session("101")

    assert session is not None
    assert session.session_uuid == "550e8400-e29b-41d4-a716-446655440000"
    assert client.calls == [("fake_beidou_user", "FakePassword123!")]
    assert repository.saved is existing
    assert existing.session_uuid_encrypted == "encrypted:550e8400-e29b-41d4-a716-446655440000"
    assert existing.session_expires_at is not None
    assert existing.session_expires_at.hour == 16


async def test_failed_update_keeps_existing_credential() -> None:
    """A failed upstream verification does not overwrite the existing credential."""
    existing = BeidouCredential(
        user_id=101,
        beidou_username="old_user",
        encrypted_password="old_password",
        session_uuid_encrypted="old_session",
        last_verified_at=fixed_now(),
        updated_at=fixed_now(),
    )
    repository = FakeRepository(existing)
    client = FakeClient(
        BeidouRequestError("beidou_invalid_credentials", "账号名称或账号密码输入错误", retryable=False)
    )
    service = BeidouCredentialService(repository, client, FakeCrypto(), now=fixed_now)

    with pytest.raises(BeidouRequestError):
        await service.bind_or_update(user_id=101, username="new_user", password="FakePassword123!")

    assert repository.credential is existing
    assert repository.saved is None


async def test_unbind_is_idempotent() -> None:
    """Deleting a missing credential still returns an unbound status."""
    repository = FakeRepository()
    service = BeidouCredentialService(repository, FakeClient(BeidouLoginResult("unused")), FakeCrypto(), now=fixed_now)

    status = await service.unbind(user_id=101)

    assert not status.bound
    assert repository.deleted_user_id == 101
