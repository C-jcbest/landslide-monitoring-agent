"""Schemas for Beidou credential binding APIs."""

from datetime import datetime

from pydantic import BaseModel, Field, SecretStr, field_validator


class BeidouCredentialStatusResponse(BaseModel):
    """Safe credential binding status returned to clients."""

    bound: bool = Field(..., description="Whether the current user has bound Beidou credentials.")
    username: str | None = Field(default=None, description="Bound Beidou username when present.")
    last_verified_at: datetime | None = Field(default=None, description="Last successful upstream verification time.")
    session_expires_at: datetime | None = Field(default=None, description="Estimated cached upstream session expiry.")


class BeidouCredentialUpsertRequest(BaseModel):
    """Request body for binding or updating Beidou credentials."""

    username: str = Field(..., min_length=1, max_length=64)
    password: SecretStr = Field(..., min_length=12, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Reject blank usernames after trimming whitespace."""
        username = value.strip()
        if not username:
            raise ValueError("username cannot be blank")
        return username
