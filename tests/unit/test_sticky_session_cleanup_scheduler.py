from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest

import app.modules.sticky_sessions.cleanup_scheduler as cleanup_scheduler
from app.core.config.settings import Settings
from app.core.utils.time import utcnow
from app.db.models import DashboardSettings

pytestmark = pytest.mark.unit


class _FakeLeader:
    """Leader stub that always runs the guarded body, bypassing the DB lease."""

    async def run_if_leader(self, fn: Callable[[], Awaitable[object]]) -> object:
        return await fn()


def test_build_sticky_session_cleanup_scheduler_respects_enabled_setting(monkeypatch) -> None:
    settings = SimpleNamespace(sticky_session_cleanup_enabled=False)
    monkeypatch.setattr(cleanup_scheduler, "get_settings", lambda: settings)
    monkeypatch.setattr(cleanup_scheduler, "_CLEANUP_INTERVAL_SECONDS", 42)

    scheduler = cleanup_scheduler.build_sticky_session_cleanup_scheduler()

    assert scheduler.interval_seconds == 42
    assert scheduler.enabled is False


@pytest.mark.asyncio
async def test_cleanup_once_purges_prompt_cache_only(monkeypatch) -> None:
    """_cleanup_once should purge prompt-cache entries by affinity TTL.
    STICKY_THREAD is never purged here. CODEX_SESSION is only ever purged
    via the separate, account-status-gated purge_stale_hard_codex_session_mappings
    call (see test_sticky_repository.py), never by this TTL-based path."""
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=600,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=600,
    )

    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )

    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=5)
    sticky_repo.purge_before = AsyncMock(return_value=0)
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=2)
    bridge_repo.purge_abandoned_before = AsyncMock(return_value=1)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=3)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=0)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(
        interval_seconds=60,
        enabled=True,
    )

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", True),
    ):
        await scheduler._cleanup_once()

    sticky_repo.purge_prompt_cache_before.assert_called_once()
    sticky_repo.purge_before.assert_not_called()
    bridge_repo.purge_closed_before.assert_called_once()
    bridge_repo.purge_abandoned_before.assert_called_once()
    bridge_repo.purge_retry_circuits_before.assert_called_once()
    bridge_repo.purge_operation_spool.assert_called_once()
    ring_service.purge_stale_before.assert_called_once()
    sticky_repo.purge_stale_hard_codex_session_mappings.assert_called_once()
    passed_cutoff = sticky_repo.purge_stale_hard_codex_session_mappings.call_args.args[0]
    expected_cutoff = utcnow() - timedelta(seconds=cleanup_scheduler._STALE_HARD_CODEX_SESSION_UNAVAILABLE_SECONDS)
    assert abs((passed_cutoff - expected_cutoff).total_seconds()) < 5


@pytest.mark.asyncio
async def test_cleanup_once_skips_bridge_purge_when_schema_is_not_ready(monkeypatch) -> None:
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=600,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=600,
    )

    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )

    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=0)
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=0)
    bridge_repo.purge_abandoned_before = AsyncMock(return_value=0)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=0)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=0)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(
        interval_seconds=60,
        enabled=True,
    )

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", False),
        patch.object(
            cleanup_scheduler,
            "missing_durable_bridge_tables",
            AsyncMock(return_value=("http_bridge_sessions",)),
        ),
    ):
        await scheduler._cleanup_once()

    sticky_repo.purge_prompt_cache_before.assert_called_once()
    bridge_repo.purge_closed_before.assert_not_called()
    bridge_repo.purge_abandoned_before.assert_not_called()
    bridge_repo.purge_retry_circuits_before.assert_not_called()
    ring_service.purge_stale_before.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_once_purges_bridge_when_schema_exists_after_startup_flag_reset(monkeypatch) -> None:
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=600,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=600,
    )

    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )

    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=0)
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=1)
    bridge_repo.purge_abandoned_before = AsyncMock(return_value=0)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=0)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=2)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(
        interval_seconds=60,
        enabled=True,
    )

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", False),
        patch.object(cleanup_scheduler, "missing_durable_bridge_tables", AsyncMock(return_value=())),
    ):
        await scheduler._cleanup_once()

    sticky_repo.purge_prompt_cache_before.assert_called_once()
    bridge_repo.purge_closed_before.assert_called_once()
    bridge_repo.purge_abandoned_before.assert_called_once()
    bridge_repo.purge_retry_circuits_before.assert_called_once()
    bridge_repo.purge_operation_spool.assert_called_once()
    ring_service.purge_stale_before.assert_called_once()


def test_abandoned_bridge_retention_covers_prompt_cache_reuse_window() -> None:
    """Abandoned-row retention must be at least the longest bridge reuse TTL."""
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=1800,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=3600,
    )
    app_settings = SimpleNamespace(
        http_responses_session_bridge_idle_ttl_seconds=120.0,
        http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
    )

    retention = cleanup_scheduler._abandoned_bridge_retention_seconds(
        cast(DashboardSettings, dashboard_settings),
        cast(Settings, app_settings),
    )

    assert retention == 3600.0

    app_settings.http_responses_session_bridge_codex_idle_ttl_seconds = 7200.0
    retention = cleanup_scheduler._abandoned_bridge_retention_seconds(
        cast(DashboardSettings, dashboard_settings),
        cast(Settings, app_settings),
    )
    assert retention == 7200.0


@pytest.mark.asyncio
async def test_cleanup_once_gates_abandoned_purge_on_prompt_cache_reuse_ttl(monkeypatch) -> None:
    """An in-reuse-window prompt-cache session must not have its ACTIVE durable
    row purged: the abandoned cutoff must honor the prompt-cache idle TTL even
    when the affinity max age is shorter."""
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=1800,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=3600,
    )

    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )

    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=0)
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=0)
    bridge_repo.purge_abandoned_before = AsyncMock(return_value=0)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=0)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=0)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(
        interval_seconds=60,
        enabled=True,
    )

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", True),
    ):
        await scheduler._cleanup_once()

    closed_cutoff = bridge_repo.purge_closed_before.call_args.args[0]
    abandoned_cutoff = bridge_repo.purge_abandoned_before.call_args.args[0]
    # Closed rows use the 1800s affinity cutoff; abandoned ACTIVE/DRAINING rows
    # must be retained for the full 3600s prompt-cache reuse window.
    gap_seconds = (closed_cutoff - abandoned_cutoff).total_seconds()
    assert abs(gap_seconds - 1800.0) < 5.0


@pytest.mark.asyncio
async def test_cleanup_once_retains_operation_purge_when_sticky_cleanup_disabled(monkeypatch) -> None:
    settings_repo = AsyncMock()
    sticky_repo = AsyncMock()
    bridge_repo = AsyncMock()
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(http_responses_session_bridge_operation_spool_retention_seconds=604800.0),
    )
    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(interval_seconds=60, enabled=False)

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", True),
    ):
        await scheduler._cleanup_once()

    settings_repo.get_or_create.assert_not_awaited()
    sticky_repo.purge_prompt_cache_before.assert_not_awaited()
    bridge_repo.purge_closed_before.assert_not_awaited()
    bridge_repo.purge_operation_spool.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_once_bumps_http_bridge_purge_only_when_abandoned_rows_deleted(monkeypatch) -> None:
    """Issue #1354 fix (b): the leader signals owner replicas through the
    http_bridge_purge invalidation namespace exactly when the abandoned purge
    actually deleted rows."""
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=600,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=600,
    )
    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )
    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=0)
    sticky_repo.purge_before = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=0)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    # The signal is emitted per COMMITTED BATCH, not once per run: deletions
    # commit inside the repository loop, so a run killed mid-way must still
    # have signalled the batches that already landed.
    committed_batches = [2, 3]
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=0)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=0)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)

    async def purge_abandoned_before(cutoff, *, on_batch_committed=None, **kwargs):
        assert on_batch_committed is not None, "scheduler must pass a per-batch signal"
        for batch in committed_batches:
            await on_batch_committed(batch)
        return sum(committed_batches)

    bridge_repo.purge_abandoned_before = AsyncMock(side_effect=purge_abandoned_before)
    poller = Mock()
    poller.bump = AsyncMock(return_value=True)
    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(interval_seconds=60, enabled=True)

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", True),
    ):
        await scheduler._cleanup_once()

    assert poller.bump.await_count == len(committed_batches)
    assert all(call.args == (cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE,) for call in poller.bump.await_args_list)
    poller.request_bump.assert_not_called()


@pytest.mark.asyncio
async def test_signal_abandoned_bridge_purge_completes_write_under_cancellation() -> None:
    """The callback runs only after its batch is committed, so a shutdown that
    cancels the scheduler mid-write must not drop the signal for rows that are
    durably gone. CancelledError is a BaseException and would bypass the
    failure fallback, so the write is shielded and drained before propagating.
    """
    started = asyncio.Event()
    release = asyncio.Event()
    completed = False

    async def slow_bump(namespace: str) -> bool:
        nonlocal completed
        started.set()
        await release.wait()
        completed = True
        return True

    poller = Mock()
    poller.bump = AsyncMock(side_effect=slow_bump)

    with patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller):
        signal_task = asyncio.create_task(cleanup_scheduler._signal_abandoned_bridge_purge(4))
        await asyncio.wait_for(started.wait(), timeout=1.0)
        signal_task.cancel()
        await asyncio.sleep(0)
        # The shielded write survives the cancellation and is drained.
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await signal_task

    assert completed is True, "shielded bump must complete before cancellation propagates"
    # It persisted, so no retry is queued.
    poller.request_bump.assert_not_called()


@pytest.mark.asyncio
async def test_signal_abandoned_bridge_purge_queues_retry_when_cancelled_write_never_lands() -> None:
    """If the shielded write cannot land within the drain grace, the bump is
    queued for retry rather than silently lost."""
    started = asyncio.Event()

    async def never_finishes(namespace: str) -> bool:
        started.set()
        await asyncio.Event().wait()
        return True

    poller = Mock()
    poller.bump = AsyncMock(side_effect=never_finishes)

    with (
        patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller),
        patch.object(cleanup_scheduler, "_PURGE_SIGNAL_CANCELLATION_GRACE_SECONDS", 0.05),
    ):
        signal_task = asyncio.create_task(cleanup_scheduler._signal_abandoned_bridge_purge(4))
        await asyncio.wait_for(started.wait(), timeout=1.0)
        signal_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await signal_task

    poller.request_bump.assert_called_once_with(cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE)


@pytest.mark.asyncio
async def test_signal_abandoned_bridge_purge_falls_back_and_survives_bump_errors() -> None:
    """A signalling failure must never abort the purge: a False return and a
    raising bump both fall back to the poller's retry queue."""
    poller = Mock()
    poller.bump = AsyncMock(return_value=False)
    with patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller):
        await cleanup_scheduler._signal_abandoned_bridge_purge(2)
    poller.request_bump.assert_called_once_with(cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE)

    poller = Mock()
    poller.bump = AsyncMock(side_effect=RuntimeError("db down"))
    with patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller):
        await cleanup_scheduler._signal_abandoned_bridge_purge(5)
    poller.request_bump.assert_called_once_with(cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE)

    # No poller installed (e.g. outside the lifespan) is a no-op, not a crash.
    with patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: None):
        await cleanup_scheduler._signal_abandoned_bridge_purge(1)


@pytest.mark.asyncio
async def test_cleanup_once_retries_http_bridge_purge_bump_when_persist_fails(monkeypatch) -> None:
    dashboard_settings = SimpleNamespace(
        openai_cache_affinity_max_age_seconds=600,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=600,
    )
    settings_repo = AsyncMock()
    settings_repo.get_or_create = AsyncMock(return_value=dashboard_settings)
    monkeypatch.setattr(
        cleanup_scheduler,
        "get_settings",
        lambda: SimpleNamespace(
            http_responses_session_bridge_idle_ttl_seconds=120.0,
            http_responses_session_bridge_codex_idle_ttl_seconds=900.0,
            http_responses_session_bridge_operation_spool_retention_seconds=604800.0,
        ),
    )
    sticky_repo = AsyncMock()
    sticky_repo.purge_stale_hard_codex_session_mappings = AsyncMock(return_value=0)
    sticky_repo.purge_prompt_cache_before = AsyncMock(return_value=0)
    sticky_repo.purge_before = AsyncMock(return_value=0)
    bridge_repo = AsyncMock()
    bridge_repo.purge_closed_before = AsyncMock(return_value=0)

    async def purge_abandoned_before(cutoff, *, on_batch_committed=None, **kwargs):
        assert on_batch_committed is not None
        await on_batch_committed(3)
        return 3

    bridge_repo.purge_abandoned_before = AsyncMock(side_effect=purge_abandoned_before)
    bridge_repo.purge_retry_circuits_before = AsyncMock(return_value=0)
    bridge_repo.purge_operation_spool = AsyncMock(return_value=0)
    ring_service = AsyncMock()
    ring_service.purge_stale_before = AsyncMock(return_value=0)
    poller = Mock()
    poller.bump = AsyncMock(return_value=False)

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = cleanup_scheduler.StickySessionCleanupScheduler(interval_seconds=60, enabled=True)

    with (
        patch.object(cleanup_scheduler, "get_background_session", FakeSession),
        patch.object(cleanup_scheduler, "SettingsRepository", return_value=settings_repo),
        patch.object(cleanup_scheduler, "StickySessionsRepository", return_value=sticky_repo),
        patch.object(cleanup_scheduler, "DurableBridgeRepository", return_value=bridge_repo),
        patch.object(cleanup_scheduler, "RingMembershipService", return_value=ring_service),
        patch.object(cleanup_scheduler, "_get_leader_election", lambda: _FakeLeader()),
        patch.object(cleanup_scheduler, "get_cache_invalidation_poller", lambda: poller),
        patch.object(cleanup_scheduler.startup_module, "_bridge_durable_schema_ready", True),
    ):
        await scheduler._cleanup_once()

    poller.bump.assert_awaited_once_with(cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE)
    poller.request_bump.assert_called_once_with(cleanup_scheduler.NAMESPACE_HTTP_BRIDGE_PURGE)
