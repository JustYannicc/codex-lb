"""Join retry claims, Codex context ownership, and usage reset indexing."""

from __future__ import annotations

revision = "20260905_140000_merge_retry_claim_and_codex_context_heads"
down_revision = (
    "20260829_000000_add_retry_circuit_admission_claim_marker",
    "20260905_120000_add_codex_context_ownership",
    "20260904_000000_add_usage_reset_transition_index",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
