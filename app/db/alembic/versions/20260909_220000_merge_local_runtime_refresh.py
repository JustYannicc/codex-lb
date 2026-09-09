"""Join the accepted local aggregate and current upstream migrations."""

from __future__ import annotations

revision = "20260909_220000_merge_local_runtime_refresh"
down_revision = (
    "20260905_140000_merge_retry_claim_and_codex_context_heads",
    "20260909_120000_merge_usage_reset_recovery",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
