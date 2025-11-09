"""Add session_records table

Revision ID: c5d4b2d6e8f0
Revises: b2e3a94f5a1c
Create Date: 2025-11-08 00:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c5d4b2d6e8f0"
down_revision: Union[str, Sequence[str], None] = "b2e3a94f5a1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create session_records table."""
    frontend_type_enum = postgresql.ENUM(
        "TELEGRAM",
        "DISCORD",
        "WEB",
        "MOBILE",
        "API",
        name="frontendtype",
        create_type=False,
    )

    op.create_table(
        "session_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("frontend_type", frontend_type_enum, nullable=False),
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("current_agent", sa.String(length=100), nullable=True),
        sa.Column("locale", sa.String(length=10), nullable=True),
        sa.Column("state_blob", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("frontend_type", "chat_id", name="uq_session_records_frontend_chat"),
    )
    op.create_index("idx_session_records_user_id", "session_records", ["user_id"], unique=False)
    op.create_index("idx_session_records_expires_at", "session_records", ["expires_at"], unique=False)
    op.create_index("idx_session_records_last_activity_at", "session_records", ["last_activity_at"], unique=False)


def downgrade() -> None:
    """Drop session_records table."""
    op.drop_index("idx_session_records_last_activity_at", table_name="session_records")
    op.drop_index("idx_session_records_expires_at", table_name="session_records")
    op.drop_index("idx_session_records_user_id", table_name="session_records")
    op.drop_table("session_records")
