"""add retry-circuit admission claim lease

Revision ID: 20260829_000000_add_retry_circuit_admission_claim_marker
Revises: 20260830_000000_add_quota_warmup_claim_expiry
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_000000_add_retry_circuit_admission_claim_marker"
down_revision = "20260830_000000_add_quota_warmup_claim_expiry"
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
    # This is a forward-only expansion of the retry admission contract. The
    # nullable receipt columns are the durable fence for an in-flight replay;
    # dropping them during rollback would erase that fence and allow a second
    # replay to be admitted for the same generation. Keep the columns and any
    # receipts intact while Alembic moves its version marker backward.
    pass
