"""Join the reset-transition index to the current upstream schema."""

from __future__ import annotations

revision = "20260909_120000_merge_usage_reset_recovery"
down_revision = (
    "20260909_110000_model_context_window_overrides",
    "20260904_000000_add_usage_reset_transition_index",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
