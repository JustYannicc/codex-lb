"""Discovery migration preserves existing manual source data across rollback."""

from __future__ import annotations

from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

_PARENT = "20260910_000000_request_logs_missing_cost_index"
_HEAD = "20260910_000000_add_cpa_catalog_discovery"


def test_cpa_catalog_migration_preserves_manual_sources(tmp_path):
    path = tmp_path / "cpa-migration.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    config = _build_alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == [_HEAD]
    run_upgrade(url, _PARENT, bootstrap_legacy=False)
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO model_sources (id, name, base_url) VALUES ('retained', 'Manual', 'https://example.invalid/v1')"
                )
            )
            connection.execute(
                text("INSERT INTO model_source_models (source_id, model) VALUES ('retained', 'manual-model')")
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT catalog_mode, catalog_refresh_token, catalog_next_refresh_at "
                    "FROM model_sources WHERE id = 'retained'"
                )
            ).one()
            assert tuple(row) == ("manual", None, None)
            identity = connection.execute(
                text("SELECT id FROM model_source_models WHERE source_id = 'retained'")
            ).scalar_one()
        command.downgrade(config, _PARENT)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT id FROM model_source_models WHERE source_id = 'retained'")).scalar_one()
                == identity
            )
            assert (
                connection.execute(text("SELECT catalog_mode FROM model_sources WHERE id = 'retained'")).scalar_one()
                == "manual"
            )
    finally:
        engine.dispose()
