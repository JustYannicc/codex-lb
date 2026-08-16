"""add account pending-deletion marker columns

Revision ID: 20260816_000000_add_account_pending_deletion
Revises: 20260812_120000_add_sticky_abandonment_scope
Create Date: 2026-08-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260816_000000_add_account_pending_deletion"
down_revision = "20260812_120000_add_sticky_abandonment_scope"
branch_labels = None
depends_on = None

_TABLE = "accounts"


def _columns(bind) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind)
    if "delete_requested_at" not in columns:
        op.add_column(_TABLE, sa.Column("delete_requested_at", sa.DateTime(), nullable=True))
    if "delete_history_requested" not in columns:
        op.add_column(
            _TABLE,
            sa.Column(
                "delete_history_requested",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind)
    if "delete_history_requested" in columns:
        op.drop_column(_TABLE, "delete_history_requested")
    if "delete_requested_at" in columns:
        op.drop_column(_TABLE, "delete_requested_at")
