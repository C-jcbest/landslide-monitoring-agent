"""User-scoped Beidou platform credential model."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field

from app.models.base import BaseModel


class BeidouCredential(BaseModel, table=True):
    """Encrypted Beidou upstream credential bound to a local user."""

    __tablename__ = "beidou_credential"  # pyright: ignore[reportAssignmentType, reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    beidou_username: str = Field(index=True)
    encrypted_password: str
    session_uuid_encrypted: Optional[str] = Field(default=None)
    session_expires_at: Optional[datetime] = Field(default=None)
    last_verified_at: datetime
    updated_at: datetime
