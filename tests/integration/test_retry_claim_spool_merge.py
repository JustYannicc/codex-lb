"""Exercise public head upgrades from both populated receipt/spool branches."""

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


@pytest.mark.parametrize("parent", _PARENTS, ids=["receipt-parent", "spool-parent"])
def test_public_head_upgrade_and_merge_only_downgrade_preserve_populated_parents(tmp_path: Path, parent: str) -> None:
    path = tmp_path / "receipt-spool.sqlite"
    _cli(path, "upgrade", parent)
    assert _revisions(path) == (parent,)
    _seed_branch(path, parent)
    before = _state(path)

    assert f"current_revision={_MERGE}" in _cli(path, "upgrade", "head")
    assert _revisions(path) == (_MERGE,)
    check = _cli(path, "check")
    assert "migration_policy=ok" in check
    assert "schema_drift=none" in check
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
    assert _revisions(path) == tuple(sorted(_PARENTS))
    assert _state(path) == populated
    assert f"current_revision={_MERGE}" in _cli(path, "upgrade", "head")
    assert _revisions(path) == (_MERGE,)
    assert _state(path) == populated
    assert "schema_drift=none" in _cli(path, "check")
