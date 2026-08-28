from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.db.recover as recover_module
import app.db.sqlite_utils as sqlite_utils_module
from app.db.backup import create_sqlite_pre_migration_backup


class _TrackedConnection(sqlite3.Connection):
    __slots__ = ("closed",)

    def __init__(self, database: str) -> None:
        super().__init__(database)
        self.closed = False

    def close(self) -> None:
        self.closed = True
        super().close()


def _track_connections(monkeypatch: pytest.MonkeyPatch) -> list[_TrackedConnection]:
    connections: list[_TrackedConnection] = []

    def connect(database: str | Path, *_args: object, **_kwargs: object) -> sqlite3.Connection:
        connection = _TrackedConnection(str(database))
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite_utils_module.sqlite3, "connect", connect)
    return connections


def _close_connections(connections: list[_TrackedConnection]) -> None:
    for connection in connections:
        connection.close()


def test_backup_closes_connections_before_rotating_old_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "store.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('alpha')")

    connections = _track_connections(monkeypatch)
    base_time = datetime(2026, 7, 29, tzinfo=timezone.utc)

    try:
        first_backup = create_sqlite_pre_migration_backup(db_path, max_files=1, now=base_time)
        second_backup = create_sqlite_pre_migration_backup(
            db_path,
            max_files=1,
            now=base_time + timedelta(minutes=1),
        )

        assert not first_backup.exists()
        assert second_backup.exists()
        assert connections
        assert all(connection.closed for connection in connections)
    finally:
        _close_connections(connections)


def test_recover_cli_closes_connections_before_replacing_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "store.db"
    output_path = tmp_path / "recovered.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('alpha')")

    connections = _track_connections(monkeypatch)
    rename_checks: list[bool] = []
    path_type = type(db_path)
    real_replace = path_type.replace

    def replace_without_open_sqlite_handles(path: Path, target: str | Path) -> Path:
        rename_checks.append(all(connection.closed for connection in connections))
        return real_replace(path, target)

    monkeypatch.setattr(path_type, "replace", replace_without_open_sqlite_handles)

    try:
        exit_code = recover_module.main(
            [
                "--db",
                str(db_path),
                "--output",
                str(output_path),
                "--replace",
            ]
        )

        corrupt_backups = list(tmp_path.glob("store.db.corrupt-*"))
        assert exit_code == 0
        assert len(corrupt_backups) == 1
        assert db_path.exists()
        assert not output_path.exists()
        assert connections
        assert all(connection.closed for connection in connections)
        assert rename_checks == [True, True]

        with closing(sqlite3.connect(db_path)) as connection:
            assert connection.execute("SELECT name FROM items").fetchall() == [("alpha",)]
    finally:
        _close_connections(connections)


def test_recover_replace_removes_sqlite_sidecars_before_installing_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source WAL must not attach to the recovered database after rename."""
    db_path = tmp_path / "store.db"
    output_path = tmp_path / "recovered.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('base')")

    for suffix in ("-wal", "-shm", "-journal", "-mj12345678"):
        (tmp_path / f"{output_path.name}{suffix}").write_bytes(b"stale output sidecar")

    held_source_connections: list[sqlite3.Connection] = []
    real_load_dump = recover_module._load_dump

    def _load_dump_then_leave_source_wal(path: Path) -> str:
        dump = real_load_dump(path)
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("INSERT INTO items (name) VALUES ('stale-after-dump')")
        connection.commit()
        held_source_connections.append(connection)
        return dump

    monkeypatch.setattr(recover_module, "_load_dump", _load_dump_then_leave_source_wal)

    try:
        recover_module.recover_sqlite_db(
            recover_module.RecoveryOptions(source=db_path, output=output_path, replace=True)
        )
        held_source_connections[0].close()

        with closing(sqlite3.connect(db_path)) as connection:
            assert connection.execute("SELECT name FROM items").fetchall() == [("base",)]

        for path in (db_path, output_path):
            for suffix in ("-wal", "-shm", "-journal", "-mj12345678"):
                assert not Path(f"{path}{suffix}").exists()
    finally:
        for connection in held_source_connections:
            connection.close()


def test_recover_replace_blocks_writes_across_the_install_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An active source connection cannot write while recovery replaces it."""
    db_path = tmp_path / "store.db"
    output_path = tmp_path / "recovered.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('base')")

    writer = sqlite3.connect(db_path, timeout=0, isolation_level=None)
    write_attempts: list[str] = []
    real_write_dump = recover_module._write_dump

    def _write_dump_then_attempt_source_write(output: Path, dump: str) -> None:
        try:
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("INSERT INTO items (name) VALUES ('raced')")
            writer.commit()
            write_attempts.append("wrote")
        except sqlite3.OperationalError as exc:
            writer.rollback()
            write_attempts.append(str(exc).lower())
        real_write_dump(output, dump)

    monkeypatch.setattr(recover_module, "_write_dump", _write_dump_then_attempt_source_write)

    try:
        recover_module.recover_sqlite_db(
            recover_module.RecoveryOptions(source=db_path, output=output_path, replace=True)
        )
    finally:
        writer.close()

    assert write_attempts == ["database is locked"]
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("INSERT INTO items (name) VALUES ('after')")
        assert connection.execute("SELECT name FROM items ORDER BY rowid").fetchall() == [
            ("base",),
            ("after",),
        ]


def test_recover_replace_fails_closed_on_partial_sidecar_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sidecar removal error must not move either database."""
    db_path = tmp_path / "store.db"
    output_path = tmp_path / "recovered.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('base')")

    blocked_sidecar = tmp_path / "store.db-mj12345678"
    blocked_sidecar.write_bytes(b"unremovable")
    for suffix in ("-wal", "-shm", "-journal"):
        (tmp_path / f"store.db{suffix}").write_bytes(b"stale")

    real_unlink = type(blocked_sidecar).unlink

    def unlink_with_partial_failure(path: Path, *, missing_ok: bool = False) -> None:
        if path == blocked_sidecar:
            raise PermissionError("simulated sidecar cleanup failure")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(type(blocked_sidecar), "unlink", unlink_with_partial_failure)

    with pytest.raises(RuntimeError, match="failed to remove SQLite sidecars"):
        recover_module.recover_sqlite_db(
            recover_module.RecoveryOptions(source=db_path, output=output_path, replace=True)
        )

    assert db_path.exists()
    assert not list(tmp_path.glob("store.db.corrupt-*"))
    assert output_path.exists()
    assert blocked_sidecar.exists()
    assert not (tmp_path / "store.db-wal").exists()
    assert not (tmp_path / "store.db-shm").exists()
    assert not (tmp_path / "store.db-journal").exists()


def test_recover_replace_fails_closed_when_source_is_busy(tmp_path: Path) -> None:
    """A conflicting source writer must prevent replacement before any rename."""
    db_path = tmp_path / "store.db"
    output_path = tmp_path / "recovered.db"
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("CREATE TABLE items (name TEXT NOT NULL)")
        connection.execute("INSERT INTO items (name) VALUES ('base')")

    writer = sqlite3.connect(db_path, timeout=0, isolation_level=None)
    writer.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(RuntimeError, match="could not acquire exclusive SQLite recovery lock"):
            recover_module.recover_sqlite_db(
                recover_module.RecoveryOptions(source=db_path, output=output_path, replace=True)
            )
    finally:
        writer.rollback()
        writer.close()

    assert db_path.exists()
    assert not output_path.exists()
    assert not list(tmp_path.glob("store.db.corrupt-*"))


def test_recover_sidecar_cleanup_treats_wildcard_database_names_literally(tmp_path: Path) -> None:
    """A wildcard in the database name must not broaden master-journal cleanup."""
    db_path = tmp_path / "store*.db"
    target_master_journal = tmp_path / "store*.db-mj12345678"
    unrelated_master_journal = tmp_path / "storeOTHER.db-mj12345678"
    target_master_journal.write_bytes(b"target")
    unrelated_master_journal.write_bytes(b"unrelated")

    recover_module._remove_sqlite_sidecars(db_path)

    assert not target_master_journal.exists()
    assert unrelated_master_journal.read_bytes() == b"unrelated"
