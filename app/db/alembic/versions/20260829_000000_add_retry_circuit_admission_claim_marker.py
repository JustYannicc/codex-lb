"""add retry-circuit admission claim lease

Revision ID: 20260829_000000_add_retry_circuit_admission_claim_marker
Revises: 20260828_000000_add_accounts_chatgpt_identity_index
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_000000_add_retry_circuit_admission_claim_marker"
down_revision = "20260828_000000_add_accounts_chatgpt_identity_index"
branch_labels = None
depends_on = None

_TABLE = "http_bridge_retry_circuits"
_COLUMNS = {
    "admission_claimed_at_epoch": sa.Float(),
    "admission_claimed_generation": sa.Integer(),
    "admission_claimed_until_epoch": sa.Float(),
}


def _columns(bind) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    if _TABLE not in sa.inspect(bind).get_table_names():
        return
    with op.batch_alter_table(_TABLE) as batch_op:
        existing = _columns(bind)
        for name, column_type in _COLUMNS.items():
            if name not in existing:
                batch_op.add_column(sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = _columns(bind)
    if not existing.intersection(_COLUMNS):
        return
    with op.batch_alter_table(_TABLE) as batch_op:
        for name in _COLUMNS:
            if name in existing:
                batch_op.drop_column(name)
