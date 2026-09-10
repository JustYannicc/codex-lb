"""Exercise populated receipt, spool, guest and user migration joins."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration

_RECEIPTS = "20260910_040000_merge_retry_claim_and_request_log_heads"
_SPOOL = "20260910_010000_dashboard_spool_retention"
_PARENTS = (_RECEIPTS, _SPOOL)
_MERGE = "20260910_160000_merge_retry_claim_spool_heads"
_GUEST = "20260908_000000_add_guest_session_generation"
_GUEST_MERGE = "20260910_170000_merge_guest_retry_claim_heads"
_GUEST_PARENTS = (_MERGE, _GUEST)
_USERS = "20260909_030000_add_audit_actor_columns"
_CURRENT_MERGE = "20260910_200000_merge_users_retry_claim_heads"
_CURRENT_PARENTS = (_GUEST_MERGE, _USERS)
_RETENTION = "http_responses_session_bridge_operation_spool_retention_seconds"
_ROOT = Path(__file__).resolve().parents[2]


def _environment(path: Path) -> dict[str, str]:
    url = f"sqlite+aiosqlite:///{path}"
    return {**os.environ, "CODEX_LB_DATABASE_URL": url, "CODEX_LB_TEST_DATABASE_URL": url}


def _run(path: Path, *args: str) -> str:
    result = subprocess.run(
        args,
        cwd=_ROOT,
        env=_environment(path),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, f"{args!r}\n{result.stdout}\n{result.stderr}"
    return result.stdout


def _cli(path: Path, *args: str) -> str:
    return _run(path, str(Path(sys.executable).with_name("codex-lb-db")), *args)


def _revisions(path: Path) -> tuple[str, ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            row[0] for row in connection.execute("SELECT version_num FROM alembic_version ORDER BY version_num")
        )


def _seed_branch(path: Path, branch: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE dashboard_settings SET sticky_threads_enabled = 0 WHERE id = 1")
        assert connection.execute("SELECT COUNT(*) FROM dashboard_settings WHERE id = 1").fetchone()[0] == 1
        connection.execute(
            """
            INSERT INTO http_bridge_retry_circuits (
                session_key_kind, session_key_hash, api_key_scope, consecutive_failures,
                cooldown_until_epoch, last_detail, updated_at_epoch, admission_generation
            ) VALUES ('session_header', 'retained-retry', '__anonymous__', 2,
                      1300.0, 'stream_incomplete', 1200.0, 7)
            """
        )
    _seed_branch_values(path, branch)


def _seed_branch_values(path: Path, branch: str) -> None:
    with sqlite3.connect(path) as connection:
        if branch == _SPOOL:
            connection.execute(f"UPDATE dashboard_settings SET {_RETENTION} = 98765.5 WHERE id = 1")
        elif branch == _GUEST:
            connection.execute("UPDATE dashboard_settings SET guest_session_generation = 17 WHERE id = 1")
        else:
            connection.execute(
                """
                UPDATE http_bridge_retry_circuits SET admission_claimed_at_epoch = 1201.25,
                    admission_claimed_generation = 7, admission_claimed_until_epoch = 4102444800.0
                WHERE session_key_hash = 'retained-retry'
                """
            )


def _state(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        schema = [
            tuple(row)
            for row in connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema "
                "WHERE name != 'alembic_version' AND tbl_name != 'alembic_version' "
                "ORDER BY type, name"
            )
        ]
        tables = [row[1] for row in schema if row[0] == "table"]
        rows = {
            table: [dict(row) for row in connection.execute('SELECT * FROM "' + table.replace('"', '""') + '"')]
            for table in tables
        }
        return {"schema": schema, "rows": rows}


def _assert_parent_rows_preserved(before: dict[str, Any], after: dict[str, Any]) -> None:
    for table, expected_rows in before["rows"].items():
        actual_rows = after["rows"][table]
        assert len(actual_rows) == len(expected_rows), table
        for expected, actual in zip(expected_rows, actual_rows, strict=True):
            assert {column: actual[column] for column in expected} == expected, table


def _downgrade_to_parent(path: Path, parent: str) -> None:
    # Name the parent: a relative -1 walk is ambiguous at a merge.
    # The public DB CLI has no downgrade command; invoke Alembic with the same isolated URL.
    _run(
        path,
        sys.executable,
        "-c",
        "import os, sys; from alembic import command; from app.db.migrate import _build_alembic_config; "
        "command.downgrade(_build_alembic_config(os.environ['CODEX_LB_DATABASE_URL']), sys.argv[1])",
        parent,
    )


@pytest.mark.parametrize("parent", _PARENTS, ids=["receipt-parent", "spool-parent"])
def test_historical_merge_upgrade_and_downgrade_preserve_populated_parents(tmp_path: Path, parent: str) -> None:
    path = tmp_path / "receipt-spool.sqlite"
    _cli(path, "upgrade", parent)
    assert _revisions(path) == (parent,)
    _seed_branch(path, parent)
    before = _state(path)

    assert f"current_revision={_MERGE}" in _cli(path, "upgrade", _MERGE)
    assert _revisions(path) == (_MERGE,)
    merged = _state(path)
    _assert_parent_rows_preserved(before, merged)
    assert _RETENTION in merged["rows"]["dashboard_settings"][0]
    retry = merged["rows"]["http_bridge_retry_circuits"][0]
    assert {
        "admission_claimed_at_epoch",
        "admission_claimed_generation",
        "admission_claimed_until_epoch",
    } <= retry.keys()

    # Populate the other branch too. A live receipt must survive this no-op downgrade.
    _seed_branch_values(path, _SPOOL if parent == _RECEIPTS else _RECEIPTS)
    populated = _state(path)
    assert populated["rows"]["dashboard_settings"][0][_RETENTION] == 98765.5
    assert populated["rows"]["http_bridge_retry_circuits"][0]["admission_claimed_until_epoch"] == 4102444800.0
    _downgrade_to_parent(path, parent)
    assert _revisions(path) == tuple(sorted(_PARENTS))
    assert _state(path) == populated
    assert f"current_revision={_MERGE}" in _cli(path, "upgrade", _MERGE)
    assert _revisions(path) == (_MERGE,)
    assert _state(path) == populated
    assert f"current_revision={_CURRENT_MERGE}" in _cli(path, "upgrade", "head")
    assert _revisions(path) == (_CURRENT_MERGE,)
    _assert_parent_rows_preserved(populated, _state(path))
    assert "schema_drift=none" in _cli(path, "check")


@pytest.mark.parametrize("parent", _GUEST_PARENTS, ids=["receipt-spool-parent", "guest-parent"])
def test_historical_guest_merge_and_downgrade_preserve_populated_parents(tmp_path: Path, parent: str) -> None:
    path = tmp_path / "guest-receipt.sqlite"
    _cli(path, "upgrade", parent)
    assert _revisions(path) == (parent,)
    _seed_branch(path, _RECEIPTS if parent == _MERGE else _GUEST)
    _seed_branch_values(path, _SPOOL)
    before = _state(path)

    assert f"current_revision={_GUEST_MERGE}" in _cli(path, "upgrade", _GUEST_MERGE)
    assert _revisions(path) == (_GUEST_MERGE,)
    merged = _state(path)
    _assert_parent_rows_preserved(before, merged)
    settings = merged["rows"]["dashboard_settings"][0]
    retry = merged["rows"]["http_bridge_retry_circuits"][0]
    assert settings[_RETENTION] == 98765.5
    assert settings["guest_session_generation"] == (0 if parent == _MERGE else 17)
    for column, value in (
        ("admission_claimed_at_epoch", 1201.25),
        ("admission_claimed_generation", 7),
        ("admission_claimed_until_epoch", 4102444800.0),
    ):
        assert retry[column] == (value if parent == _MERGE else None)

    _seed_branch_values(path, _GUEST if parent == _MERGE else _RECEIPTS)
    populated = _state(path)
    assert populated["rows"]["dashboard_settings"][0]["guest_session_generation"] == 17
    assert populated["rows"]["http_bridge_retry_circuits"][0]["admission_claimed_until_epoch"] == 4102444800.0
    for downgrade_parent in _GUEST_PARENTS:
        _downgrade_to_parent(path, downgrade_parent)
        assert _revisions(path) == tuple(sorted(_GUEST_PARENTS))
        assert _state(path) == populated
        assert f"current_revision={_GUEST_MERGE}" in _cli(path, "upgrade", _GUEST_MERGE)
        assert _revisions(path) == (_GUEST_MERGE,)
        assert _state(path) == populated
    assert f"current_revision={_CURRENT_MERGE}" in _cli(path, "upgrade", "head")
    assert _revisions(path) == (_CURRENT_MERGE,)
    _assert_parent_rows_preserved(populated, _state(path))
    assert "schema_drift=none" in _cli(path, "check")


def _seed_users(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO dashboard_roles (id, slug, name, kind, permissions_version) "
            "VALUES ('retained-role', 'retained-role', 'Retained role', 'custom', 9)"
        )
        connection.executemany(
            "INSERT INTO dashboard_role_grants (role_id, permission, scope) VALUES ('retained-role', ?, ?)",
            [("api_keys:read", "own"), ("accounts:read", "all")],
        )
        connection.execute(
            "INSERT INTO dashboard_users (id, username, role_id, session_generation, password_hash) "
            "VALUES ('retained-user', 'retained-user', 'retained-role', 23, 'retained-user-hash')"
        )
        connection.execute(
            "INSERT INTO dashboard_identities (id, user_id, provider, provider_key, subject) "
            "VALUES ('retained-identity', 'retained-user', 'oidc', 'retained-provider', 'retained-subject')"
        )


@pytest.mark.parametrize("parent", _CURRENT_PARENTS, ids=["guest-retry-parent", "users-parent"])
def test_public_users_head_upgrade_and_downgrade_preserve_populated_parents(tmp_path: Path, parent: str) -> None:
    path = tmp_path / "users-receipt.sqlite"
    _cli(path, "upgrade", parent)
    assert _revisions(path) == (parent,)
    _seed_branch(path, _RECEIPTS if parent == _GUEST_MERGE else _GUEST)
    _seed_branch_values(path, _SPOOL)
    _seed_branch_values(path, _GUEST)
    if parent == _USERS:
        _seed_users(path)
    else:
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE dashboard_settings SET password_hash = 'legacy-admin-hash' WHERE id = 1")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO audit_logs (id, timestamp, action, details) "
            "VALUES (700, '2026-09-10 12:00:00', 'settings.updated', 'retained-audit')"
        )
        if parent == _USERS:
            connection.execute(
                "UPDATE audit_logs SET timestamp = '2026-09-10 12:00:00.000000', "
                "actor_user_id = 'retained-user', actor_username = 'retained-user', "
                "target_type = 'settings', target_id = 'dashboard', severity = 'warning' WHERE id = 700"
            )
    before = _state(path)

    assert f"current_revision={_CURRENT_MERGE}" in _cli(path, "upgrade", "head")
    assert _revisions(path) == (_CURRENT_MERGE,)
    check = _cli(path, "check")
    assert "migration_policy=ok" in check and "schema_drift=none" in check
    merged = _state(path)
    if parent == _GUEST_MERGE:
        before["rows"]["audit_logs"][0]["timestamp"] += ".000000"
    _assert_parent_rows_preserved(before, merged)
    audit = merged["rows"]["audit_logs"][0]
    assert audit["actor_user_id"] == ("retained-user" if parent == _USERS else None)
    assert audit["target_id"] == ("dashboard" if parent == _USERS else None)
    assert audit["severity"] == ("warning" if parent == _USERS else "info")
    assert {row["slug"] for row in merged["rows"]["dashboard_roles"] if row["kind"] == "preset"} == {
        "admin",
        "operator",
        "member",
        "viewer",
        "guest",
    }
    retry = merged["rows"]["http_bridge_retry_circuits"][0]
    for column, value in (
        ("admission_claimed_at_epoch", 1201.25),
        ("admission_claimed_generation", 7),
        ("admission_claimed_until_epoch", 4102444800.0),
    ):
        assert retry[column] == (value if parent == _GUEST_MERGE else None)
    if parent == _GUEST_MERGE:
        admin = next(row for row in merged["rows"]["dashboard_users"] if row["username"] == "admin")
        assert admin["password_hash"] == "legacy-admin-hash" and admin["is_break_glass"] == 1
        _seed_users(path)
    else:
        _seed_branch_values(path, _RECEIPTS)
    populated = _state(path)
    for downgrade_parent in _CURRENT_PARENTS:
        _downgrade_to_parent(path, downgrade_parent)
        assert _revisions(path) == tuple(sorted(_CURRENT_PARENTS))
        assert _state(path) == populated
        assert f"current_revision={_CURRENT_MERGE}" in _cli(path, "upgrade", "head")
        assert _revisions(path) == (_CURRENT_MERGE,)
        assert _state(path) == populated
    assert "schema_drift=none" in _cli(path, "check")
