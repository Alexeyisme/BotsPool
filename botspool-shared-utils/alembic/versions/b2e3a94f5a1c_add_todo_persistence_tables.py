"""Add ToDo persistence tables

Revision ID: b2e3a94f5a1c
Revises: a915df10d70b
Create Date: 2025-11-07 19:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2e3a94f5a1c"
down_revision: Union[str, Sequence[str], None] = "a915df10d70b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ToDo persistence tables."""
    op.create_table(
        "todo_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_todo_profiles_user"),
    )
    op.create_index("idx_todo_profiles_user_id", "todo_profiles", ["user_id"], unique=False)

    op.create_table(
        "todo_instructions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_todo_instructions_user"),
    )
    op.create_index("idx_todo_instructions_user_id", "todo_instructions", ["user_id"], unique=False)

    op.create_table(
        "todo_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'not_started'")),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("time_to_complete", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("solutions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extra", sa.JSON(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_todo_items_user_status", "todo_items", ["user_id", "status"], unique=False)
    op.create_index("idx_todo_items_deadline", "todo_items", ["deadline"], unique=False)


def downgrade() -> None:
    """Drop ToDo persistence tables."""
    op.drop_index("idx_todo_items_deadline", table_name="todo_items")
    op.drop_index("idx_todo_items_user_status", table_name="todo_items")
    op.drop_table("todo_items")

    op.drop_index("idx_todo_instructions_user_id", table_name="todo_instructions")
    op.drop_table("todo_instructions")

    op.drop_index("idx_todo_profiles_user_id", table_name="todo_profiles")
    op.drop_table("todo_profiles")
