from __future__ import annotations

import os

import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config.settings import get_settings
from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
PARENT = "20260909_080000_dashboard_stream_bridge_budgets"
REVISION = "20260909_210000_desktop_reset_pool"


@pytest.fixture(params=["sqlite", "postgresql"])
async def migration_url(request, tmp_path):
    if request.param == "sqlite":
        return f"sqlite+aiosqlite:///{tmp_path / 'reset-pool.db'}"
    url = get_settings().database_url
    if not url.startswith("postgresql+"):
        pytest.skip("Requires CODEX_LB_TEST_DATABASE_URL pointing to a disposable PostgreSQL database")
    if url != os.environ.get("CODEX_LB_TEST_DATABASE_URL") or make_url(url).database != "codex_lb_test":
        pytest.fail(
            "Refusing to reset PostgreSQL: configure CODEX_LB_TEST_DATABASE_URL to the dedicated codex_lb_test database"
        )
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()
    return url


async def test_reset_pool_migration_defaults_existing_settings_and_round_trips(migration_url):
    url = migration_url
    await to_thread.run_sync(lambda: run_upgrade(url, PARENT, bootstrap_legacy=False))
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT COUNT(*) FROM dashboard_settings WHERE id=1")) == 1
        await to_thread.run_sync(lambda: run_upgrade(url, REVISION, bootstrap_legacy=False))
        async with engine.connect() as connection:
            assert (
                await connection.scalar(text("SELECT desktop_reset_pool_enabled FROM dashboard_settings WHERE id=1"))
                == 0
            )
        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(url), PARENT))
        await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
        assert await to_thread.run_sync(lambda: check_schema_drift(url)) == ()
    finally:
        await engine.dispose()


async def test_reset_pool_downgrade_retains_redemption_bindings(migration_url):
    url = migration_url
    await to_thread.run_sync(lambda: run_upgrade(url, REVISION, bootstrap_legacy=False))
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO desktop_reset_credit_redemptions "
                    "VALUES ('caller','attempt','deleted-owner','upstream-owner','credit',CURRENT_TIMESTAMP)"
                )
            )
        with pytest.raises(RuntimeError, match="redemption ledger"):
            await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(url), PARENT))
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT COUNT(*) FROM desktop_reset_credit_redemptions")) == 1
    finally:
        await engine.dispose()


@pytest.mark.parametrize("starting_revision", [REVISION, "20260910_000000_request_logs_missing_cost_index"])
async def test_populated_branch_upgrade_and_merge_downgrade_preserve_settings_and_bindings(
    migration_url, starting_revision
):
    url = migration_url
    await to_thread.run_sync(lambda: run_upgrade(url, starting_revision, bootstrap_legacy=False))
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("UPDATE dashboard_settings SET sticky_threads_enabled = false WHERE id=1"))
            if starting_revision == REVISION:
                await connection.execute(
                    text(
                        "INSERT INTO desktop_reset_credit_redemptions "
                        "VALUES ('caller','attempt','deleted-owner','upstream-owner','credit',CURRENT_TIMESTAMP)"
                    )
                )
        await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
        assert await to_thread.run_sync(lambda: check_schema_drift(url)) == ()
        async with engine.connect() as connection:
            assert not await connection.scalar(text("SELECT sticky_threads_enabled FROM dashboard_settings WHERE id=1"))
            assert not await connection.scalar(
                text("SELECT desktop_reset_pool_enabled FROM dashboard_settings WHERE id=1")
            )
            before = (await connection.execute(text("SELECT * FROM desktop_reset_credit_redemptions"))).all()
            assert len(before) == (1 if starting_revision == REVISION else 0)
            if before:
                assert tuple(before[0][:5]) == ("caller", "attempt", "deleted-owner", "upstream-owner", "credit")
        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(url), starting_revision))
        async with engine.connect() as connection:
            assert (await connection.execute(text("SELECT * FROM desktop_reset_credit_redemptions"))).all() == before
            revisions = set((await connection.execute(text("SELECT version_num FROM alembic_version"))).scalars())
            assert revisions == {REVISION, "20260910_000000_request_logs_missing_cost_index"}
        await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
        assert await to_thread.run_sync(lambda: check_schema_drift(url)) == ()
    finally:
        await engine.dispose()
