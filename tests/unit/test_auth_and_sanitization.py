"""Unit tests for authentication, input validation, and sanitization."""

from datetime import timedelta

import pytest
from jose import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.auth import UserCreate
from app.schemas.chat import Message, SessionTitle
from app.utils.auth import create_access_token, verify_token
from app.utils.sanitization import sanitize_dict, sanitize_email, sanitize_string, validate_password_strength

pytestmark = pytest.mark.unit


def test_access_token_round_trip_returns_subject() -> None:
    """A newly issued token should decode to its original subject."""
    token = create_access_token("101", expires_delta=timedelta(minutes=5))

    assert verify_token(token.access_token) == "101"
    assert token.token_type == "bearer"


@pytest.mark.parametrize("token", ["", "not.a.jwt.with.four.parts", "not-a-jwt"])
def test_verify_token_rejects_malformed_tokens(token: str) -> None:
    """Malformed tokens must not be accepted as authenticated subjects."""
    with pytest.raises(ValueError):
        verify_token(token)


def test_verify_token_returns_none_for_valid_signature_without_subject() -> None:
    """A syntactically valid JWT without ``sub`` is not an identity."""
    token = jwt.encode({"exp": 4_102_444_800}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    assert verify_token(token) is None


@pytest.mark.parametrize(
    "password",
    ["Sho1!rt", "alllowercase1!", "ALLUPPERCASE1!", "NoSpecial123", "NoDigits!Aa"],
)
def test_password_strength_rejects_each_missing_requirement(password: str) -> None:
    """Every documented password requirement has an independent rejection path."""
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_user_schema_accepts_strong_password() -> None:
    """Schema and service validation agree on a valid password."""
    user = UserCreate(email="USER@Example.COM", password="ValidPass1!", username="Alice")

    assert user.email == "USER@example.com"


@pytest.mark.parametrize("email", ["not-an-email", "name@invalid", "name<script>@example.com"])
def test_sanitize_email_rejects_invalid_addresses(email: str) -> None:
    """Email sanitation rejects values that cannot safely identify an account."""
    with pytest.raises(ValueError):
        sanitize_email(email)


def test_sanitizers_escape_nested_html_and_remove_null_bytes() -> None:
    """Nested request data cannot preserve HTML tags or null bytes."""
    sanitized = sanitize_dict({"message": "<b>hello</b>\0", "items": ["<script>x</script>"]})

    assert sanitized == {"message": "&lt;b&gt;hello&lt;/b&gt;", "items": [""]}
    assert sanitize_string("<em>safe</em>") == "&lt;em&gt;safe&lt;/em&gt;"


@pytest.mark.parametrize("content", ["<script>alert(1)</script>", "hello\0world", ""])
def test_message_schema_rejects_unsafe_or_empty_content(content: str) -> None:
    """Unsafe content must be rejected before it can reach the model."""
    with pytest.raises(ValidationError):
        Message(role="user", content=content)


def test_session_title_normalizes_whitespace_and_punctuation() -> None:
    """Generated titles are normalized before persistence."""
    title = SessionTitle(title="  ' Rainfall trend?  ' ")

    assert title.title == "Rainfall trend"
