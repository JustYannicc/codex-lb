"""merge quota warmup claim expiry head with the usage-history/owner-epoch merge

Revision ID: 20260806_140000_merge_quota_warmup_claim_expiry_head
Revises:
- 20260806_030000_add_quota_warmup_claim_expiry
- 20260806_130000_merge_usage_history_covering_and_bridge_owner_epoch_heads
Create Date: 2026-08-06 14:00:00.000000

The quota warmup claim-expiry revision branched from
``20260806_020000_add_usage_history_bulk_covering_indexes``, the same parent the
usage-history/owner-epoch merge already converged on, so it left the chain with
two heads. Both sides are additive; this no-op merge records the convergence so
startup and the deploy preflight see one canonical Alembic head.
"""

from __future__ import annotations

revision = "20260806_140000_merge_quota_warmup_claim_expiry_head"
down_revision = (
    "20260806_030000_add_quota_warmup_claim_expiry",
    "20260806_130000_merge_usage_history_covering_and_bridge_owner_epoch_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
