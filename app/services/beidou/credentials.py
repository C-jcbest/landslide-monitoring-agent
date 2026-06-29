"""Beidou credential binding service."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.logging import logger
from app.models.beidou_credential import BeidouCredential
from app.schemas.beidou import BeidouCredentialStatusResponse
from app.services.async_database import AsyncSessionLocal
from app.services.beidou.client import BeidouClient
from app.services.beidou.crypto import BeidouCryptoService


class CryptoService(Protocol):
    """Protocol for credential crypto helpers."""

    def encrypt(self, value: str) -> str:
        """Encrypt a secret string."""
        ...

    def decrypt(self, value: str) -> str:
        """Decrypt a secret string."""
        ...


class BeidouCredentialRepository:
    """Async repository for Beidou credential records."""

    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        """Initialize repository with an async session factory."""
        self._session_factory = session_factory

    async def get_by_user_id(self, user_id: int) -> BeidouCredential | None:
        """Return a user's Beidou credential if present."""
        async with self._session_factory() as session:
            result = await session.execute(select(BeidouCredential).where(BeidouCredential.user_id == user_id))
            return result.scalar_one_or_none()

    async def upsert(self, credential: BeidouCredential) -> BeidouCredential:
        """Insert or update a user's Beidou credential."""
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(BeidouCredential).where(BeidouCredential.user_id == credential.user_id)
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    session.add(credential)
                    saved = credential
                else:
                    existing.beidou_username = credential.beidou_username
                    existing.encrypted_password = credential.encrypted_password
                    existing.session_uuid_encrypted = credential.session_uuid_encrypted
                    existing.session_expires_at = credential.session_expires_at
                    existing.last_verified_at = credential.last_verified_at
                    existing.updated_at = credential.updated_at
                    saved = existing
                await session.commit()
                await session.refresh(saved)
                return saved
            except SQLAlchemyError:
                await session.rollback()
                raise

    async def delete_by_user_id(self, user_id: int) -> bool:
        """Delete a user's Beidou credential if present."""
        async with self._session_factory() as session:
            try:
                result = await session.execute(select(BeidouCredential).where(BeidouCredential.user_id == user_id))
                credential = result.scalar_one_or_none()
                if credential is None:
                    return False
                await session.delete(credential)
                await session.commit()
                return True
            except SQLAlchemyError:
                await session.rollback()
                raise


class BeidouCredentialService:
    """Application service for user-scoped Beidou credentials."""

    def __init__(
        self,
        repository: BeidouCredentialRepository,
        client: BeidouClient,
        crypto: CryptoService | None = None,
        *,
        now: Callable[[], datetime] | None = None,
        session_ttl_seconds: int | None = None,
    ) -> None:
        """Initialize the service with injectable dependencies."""
        self.repository = repository
        self.client = client
        self.crypto = crypto
        self._now = now or (lambda: datetime.now(UTC))
        self.session_ttl_seconds = session_ttl_seconds or settings.BEIDOU_SESSION_TTL_SECONDS

    async def get_status(self, user_id: int) -> BeidouCredentialStatusResponse:
        """Return safe Beidou credential status for a user."""
        logger.info("beidou_credential_status_requested", user_id=user_id)
        credential = await self.repository.get_by_user_id(user_id)
        if credential is None:
            return BeidouCredentialStatusResponse(bound=False)
        return _status_from_credential(credential)

    async def bind_or_update(self, user_id: int, username: str, password: str) -> BeidouCredentialStatusResponse:
        """Verify and save user-scoped Beidou credentials."""
        logger.info("beidou_credential_bind_requested", user_id=user_id, beidou_username=username)
        login_result = await self.client.login(username, password)
        crypto = self._get_crypto()
        verified_at = self._now()
        expires_at = verified_at + timedelta(seconds=self.session_ttl_seconds)
        credential = BeidouCredential(
            user_id=user_id,
            beidou_username=username,
            encrypted_password=crypto.encrypt(password),
            session_uuid_encrypted=crypto.encrypt(login_result.session_uuid),
            session_expires_at=expires_at,
            last_verified_at=verified_at,
            updated_at=verified_at,
        )
        saved = await self.repository.upsert(credential)
        logger.info("beidou_credential_saved", user_id=user_id, beidou_username=username)
        return _status_from_credential(saved)

    async def unbind(self, user_id: int) -> BeidouCredentialStatusResponse:
        """Remove a user's Beidou credential if present."""
        await self.repository.delete_by_user_id(user_id)
        logger.info("beidou_credential_unbound", user_id=user_id)
        return BeidouCredentialStatusResponse(bound=False)

    def _get_crypto(self) -> CryptoService:
        if self.crypto is None:
            self.crypto = BeidouCryptoService(settings.BEIDOU_CREDENTIAL_ENCRYPTION_KEY)
        return self.crypto


def _status_from_credential(credential: BeidouCredential) -> BeidouCredentialStatusResponse:
    return BeidouCredentialStatusResponse(
        bound=True,
        username=credential.beidou_username,
        last_verified_at=credential.last_verified_at,
        session_expires_at=credential.session_expires_at,
    )


def create_beidou_credential_service() -> BeidouCredentialService:
    """Create the production Beidou credential service."""
    return BeidouCredentialService(
        BeidouCredentialRepository(),
        BeidouClient(settings.BEIDOU_API_BASE_URL, timeout_seconds=settings.BEIDOU_API_TIMEOUT_SECONDS),
    )
