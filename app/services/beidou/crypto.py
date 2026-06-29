"""Encryption helpers for Beidou credentials."""

from cryptography.fernet import Fernet, InvalidToken


class BeidouCryptoError(Exception):
    """Raised when Beidou credential crypto is not configured or cannot decrypt."""


class BeidouCryptoService:
    """Fernet-backed encryption service for Beidou secrets."""

    def __init__(self, key: str) -> None:
        """Initialize the service with a configured Fernet key."""
        if not key:
            raise BeidouCryptoError("beidou credential encryption key is not configured")
        try:
            self._fernet = Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as e:
            raise BeidouCryptoError("beidou credential encryption key is invalid") from e

    def encrypt(self, value: str) -> str:
        """Encrypt a secret string."""
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        """Decrypt a secret string."""
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken as e:
            raise BeidouCryptoError("beidou credential value cannot be decrypted") from e
