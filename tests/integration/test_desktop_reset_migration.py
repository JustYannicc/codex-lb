from __future__ import annotations

import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config.settings import get_settings
from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade
from app.db.session import SessionLocal

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
PARENT = "20260909_080000_dashboard_stream_bridge_budgets"
REVISION = "20260909_210000_desktop_reset_pool"


@pytest.fixture(params=["sqlite", "postgresql"])
async def migration_url(request, tmp_path, db_setup):
    if request.param == "sqlite":
        return f"sqlite+aiosqlite:///{tmp_path / 'reset-pool.db'}"
    url = get_settings().database_url
    if not url.startswith("postgresql+"):
        pytest.skip("Requires CODEX_LB_TEST_DATABASE_URL pointing to a disposable PostgreSQL database")
    async with SessionLocal() as session:
        await session.execute(text("DROP SCHEMA public CASCADE"))
        await session.execute(text("CREATE SCHEMA public"))
        await session.commit()
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
