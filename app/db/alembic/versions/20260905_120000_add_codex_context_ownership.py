"""Persist Codex notes ownership and history participation."""

import sqlalchemy as sa
from alembic import op

revision = "20260905_120000_add_codex_context_ownership"
down_revision = "20260830_000000_add_quota_warmup_claim_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = [
        name for name in ("codex_context_sessions", "codex_context_participants") if inspector.has_table(name)
    ]
    if existing_tables:
        raise RuntimeError(
            "Cannot create Codex context ownership tables because tables already exist: " + ", ".join(existing_tables)
        )
    op.create_table(
        "codex_context_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("api_key_id", sa.String(), nullable=False),
        sa.Column("owner_account_id", sa.String(), nullable=False),
    )
    op.create_table(
        "codex_context_participants",
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("codex_context_sessions.session_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("account_id", sa.String(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("codex_context_participants")
    op.drop_table("codex_context_sessions")
