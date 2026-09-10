"""Persist the identity and request scope of account holds."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_010000_add_account_rejection_generation"
down_revision = "20260910_000000_request_logs_missing_cost_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("block_generation", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("accounts", sa.Column("rejected_model", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("rejected_service_tier", sa.String(), nullable=True))

    op.add_column("accounts", sa.Column("probe_claim_token", sa.String(), nullable=True))
    op.add_column("accounts", sa.Column("probe_claim_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "probe_claim_expires_at")
    op.drop_column("accounts", "probe_claim_token")
    op.drop_column("accounts", "rejected_service_tier")
    op.drop_column("accounts", "rejected_model")
    op.drop_column("accounts", "block_generation")
