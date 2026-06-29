"""Tests for Beidou credential encryption helpers."""

import pytest
from cryptography.fernet import Fernet

from app.services.beidou.crypto import BeidouCryptoError, BeidouCryptoService

pytestmark = pytest.mark.unit


def test_encrypt_decrypt_round_trip_uses_non_deterministic_ciphertext() -> None:
    """Fernet encryption hides plaintext and remains decryptable."""
    service = BeidouCryptoService(Fernet.generate_key().decode("utf-8"))

    first = service.encrypt("FakePassword123!")
    second = service.encrypt("FakePassword123!")

    assert first != "FakePassword123!"
    assert second != "FakePassword123!"
    assert first != second
    assert service.decrypt(first) == "FakePassword123!"
    assert service.decrypt(second) == "FakePassword123!"


@pytest.mark.parametrize("key", ["", "not-a-fernet-key"])
def test_invalid_or_missing_key_raises_configuration_error(key: str) -> None:
    """Invalid encryption configuration is rejected before storing credentials."""
    with pytest.raises(BeidouCryptoError):
        BeidouCryptoService(key)
