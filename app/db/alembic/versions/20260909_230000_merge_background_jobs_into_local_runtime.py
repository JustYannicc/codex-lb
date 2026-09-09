"""Join upstream background-job controls with the published local runtime."""

from __future__ import annotations

revision = "20260909_230000_merge_background_jobs_into_local_runtime"
down_revision = (
    "20260909_220000_merge_local_runtime_refresh",
    "20260909_090000_dashboard_background_job_toggles",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
