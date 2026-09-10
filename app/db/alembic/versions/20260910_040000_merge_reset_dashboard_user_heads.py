"""Join reset pooling with dashboard users without rewriting published history."""

from __future__ import annotations

revision = "20260910_040000_merge_reset_dashboard_user_heads"
down_revision = (
    "20260910_030000_merge_reset_guest_heads",
    "20260909_020000_reproject_compat_admin_credentials",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Retain both parent schemas and their stored data."""
    pass


def downgrade() -> None:
    """Restore both parent stamps without removing their schemas or data."""
    pass
