"""Add Beidou credential table.

Revision ID: 2f0f1c9b4e7a
Revises: b25d38b0cd7c
Create Date: 2026-06-29 18:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # noqa: F401

from alembic import op

revision: str = "2f0f1c9b4e7a"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "b25d38b0cd7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "beidou_credential",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("beidou_username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("encrypted_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("session_uuid_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("session_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_beidou_credential_beidou_username"),
        "beidou_credential",
        ["beidou_username"],
        unique=False,
    )
    op.create_index(op.f("ix_beidou_credential_user_id"), "beidou_credential", ["user_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_beidou_credential_user_id"), table_name="beidou_credential")
    op.drop_index(op.f("ix_beidou_credential_beidou_username"), table_name="beidou_credential")
    op.drop_table("beidou_credential")
