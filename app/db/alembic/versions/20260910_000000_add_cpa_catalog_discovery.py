"""Add opt-in CPA discovery and persisted refresh fencing."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_000000_add_cpa_catalog_discovery"
down_revision = "20260909_090000_dashboard_background_job_toggles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_sources") as batch:
        batch.add_column(sa.Column("catalog_mode", sa.String(), server_default="manual", nullable=False))
        batch.add_column(sa.Column("catalog_refresh_token", sa.String(), nullable=True))
        batch.add_column(sa.Column("catalog_next_refresh_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("model_sources") as batch:
        batch.drop_column("catalog_next_refresh_at")
        batch.drop_column("catalog_refresh_token")
        batch.drop_column("catalog_mode")
