"""Affinity observation metadata survives the public migration lifecycle."""

from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration

_PARENT = "20260910_010000_dashboard_spool_retention"
_REVISION = "20260910_143000_request_log_affinity"
_COLUMNS = ("sticky_key_source", "sticky_kind", "sticky_key_hash")


def test_populated_upgrade_and_downgrade_preserve_logs_and_ownership(tmp_path: Path) -> None:
    path = tmp_path / "affinity.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    run_upgrade(url, _PARENT, bootstrap_legacy=False)
    engine = create_engine(f"sqlite:///{path}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO accounts (id, codex_installation_id, email, plan_type, access_token_encrypted,
                    refresh_token_encrypted, id_token_encrypted, last_refresh, status)
                VALUES ('affinity-owner', 'synthetic-installation', 'synthetic@example.invalid', 'plus',
                    x'01', x'02', x'03', '2026-09-10 00:00:00', 'active')
            """)
            )
            connection.execute(
                text("""
                INSERT INTO request_logs (account_id, request_id, model, status)
                VALUES ('affinity-owner', 'synthetic-historical', 'synthetic-model', 'success')
            """)
            )
            before = dict(connection.execute(text("SELECT * FROM request_logs")).mappings().one())
            owner = tuple(connection.execute(text("SELECT * FROM accounts")).one())
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.begin() as connection:
            after = dict(connection.execute(text("SELECT * FROM request_logs")).mappings().one())
            assert {column: after.pop(column) for column in _COLUMNS} == dict.fromkeys(_COLUMNS)
            assert after == before
            connection.execute(
                text("""
                UPDATE request_logs SET sticky_key_source = 'session_id',
                    sticky_kind = 'session', sticky_key_hash = 'synthetic-hash'
            """)
            )
        command.downgrade(_build_alembic_config(url), _PARENT)
        with engine.connect() as connection:
            assert dict(connection.execute(text("SELECT * FROM request_logs")).mappings().one()) == before
            assert tuple(connection.execute(text("SELECT * FROM accounts")).one()) == owner
            assert not set(_COLUMNS) & {column["name"] for column in inspect(connection).get_columns("request_logs")}
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()


def test_fresh_upgrade_has_single_affinity_head_and_nullable_metadata(tmp_path: Path) -> None:
    path = tmp_path / "fresh.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    script = ScriptDirectory.from_config(_build_alembic_config(url))
    assert script.get_heads() == [_REVISION]
    assert script.get_revision(_REVISION).down_revision == _PARENT
    assert run_upgrade(url, "head", bootstrap_legacy=False).current_revision == _REVISION
    assert check_schema_drift(url) == ()
    engine = create_engine(f"sqlite:///{path}")
    try:
        columns = {column["name"]: column for column in inspect(engine).get_columns("request_logs")}
        assert all(columns[name]["nullable"] and columns[name]["default"] is None for name in _COLUMNS)
    finally:
        engine.dispose()


def test_bootstrap_existing_schema_preserves_affinity_values(tmp_path: Path) -> None:
    from app.db.models import Base

    path = tmp_path / "existing-schema.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_engine(f"sqlite:///{path}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO request_logs (request_id, model, status,
                    sticky_key_source, sticky_kind, sticky_key_hash)
                VALUES ('synthetic-existing', 'synthetic-model', 'success',
                    'session_id', 'session', 'synthetic-hash')
            """)
            )
            before = dict(connection.execute(text("SELECT * FROM request_logs")).mappings().one())
        result = run_upgrade(url, "head", bootstrap_legacy=True)
        assert result.current_revision == _REVISION
        assert check_schema_drift(url) == ()
        with engine.connect() as connection:
            after = dict(connection.execute(text("SELECT * FROM request_logs")).mappings().one())
            assert {name: after[name] for name in before} == before
    finally:
        engine.dispose()
