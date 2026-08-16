"""Regression tests for issue #1755: cross-test live-usage-ingestor leakage.

The unit suite runs on a session-scoped asyncio loop, so a background task
leaked by one test survives into every later test. Tests that enter the real
app lifespan start the module-global live-usage ingestor; when the lifespan is
cancelled before its shutdown path reaches ``stop_live_usage_ingestor()``
(e.g. a ``wait_for``-bounded assertion times out mid-drain), the
``live-usage-ingestor`` consumer task outlives the test and later poisons the
otel lifespan-drain test and test_proxy_utils' startup-probe loop-exception
assertions.

The two tests below are ORDER-DEPENDENT by design (pytest runs them in
definition order): the first reproduces the leak by starting the ingestor
singleton exactly like the app lifespan does and deliberately never stopping
it; the second asserts the autouse ``_stop_leaked_live_usage_ingestor`` fence
in tests/conftest.py reclaimed the consumer at the previous test's boundary.
Without the fence the second test fails with a pending
``live-usage-ingestor`` task — the coupling observed in #1755.
"""

from __future__ import annotations

import asyncio
import time

from app.core.usage import live_hub
from app.modules.usage import live_ingest


def _pending_ingestor_tasks() -> list[asyncio.Task[object]]:
    return [task for task in asyncio.all_tasks() if not task.done() and task.get_name() == "live-usage-ingestor"]


async def test_abandoned_ingestor_simulates_lifespan_cancelled_before_stop() -> None:
    # This is exactly what app.main's lifespan startup does; a lifespan
    # cancelled mid-shutdown-drain never reaches stop_live_usage_ingestor(),
    # so nothing in this test stops the singleton either. The autouse fence
    # in tests/conftest.py must reclaim it at this test's boundary.
    ingestor = live_ingest.start_live_usage_ingestor()

    assert ingestor is not None
    assert live_ingest._ingestor is ingestor
    assert live_hub._publisher is not None
    assert len(_pending_ingestor_tasks()) == 1


async def test_fence_reclaims_leaked_consumer_at_test_boundary() -> None:
    assert _pending_ingestor_tasks() == []
    assert live_ingest._ingestor is None
    assert live_hub._publisher is None


async def test_reap_consumes_and_reports_already_failed_consumer() -> None:
    # A leaked consumer can already be dead with an exception by the time the
    # fence runs (#1755 observed RuntimeError('cannot reuse already awaited
    # coroutine')). The fence must retrieve that exception — so it neither
    # crashes mid-cleanup nor resurfaces later as an unobserved-task loop
    # exception in an unrelated test — and report it for attribution.
    from tests import conftest as suite_conftest

    async def _boom() -> None:
        raise RuntimeError("cannot reuse already awaited coroutine")

    task = asyncio.create_task(_boom(), name="live-usage-ingestor")
    await asyncio.sleep(0)
    assert task.done()

    ingestor = live_ingest.LiveUsageIngestor(queue_size=1, write_min_interval_seconds=0.0)
    ingestor._consumer = task
    live_ingest._ingestor = ingestor
    live_hub.register_live_usage_publisher(ingestor.publish)

    await suite_conftest._reap_leaked_live_usage_ingestor()
    failures = suite_conftest._consume_dead_live_ingest_task_failures()

    assert failures == ["'live-usage-ingestor' died with RuntimeError('cannot reuse already awaited coroutine')"]
    assert live_ingest._ingestor is None
    assert live_hub._publisher is None
    assert _pending_ingestor_tasks() == []
    # Retrieval is idempotent: a second pass reports nothing.
    assert suite_conftest._consume_dead_live_ingest_task_failures() == []


async def test_reap_sweeps_orphaned_tasks_not_tracked_by_singleton() -> None:
    # A stop that is itself cancelled between clearing the module global and
    # awaiting the ingestor's tasks leaves pending tasks no singleton tracks;
    # the reap's name-based sweep must still cancel and await both the
    # consumer and the trailing cache-invalidation sleeper.
    from tests import conftest as suite_conftest

    async def _pending_forever() -> None:
        await asyncio.Event().wait()

    consumer = asyncio.create_task(_pending_forever(), name="live-usage-ingestor")
    trailing = asyncio.create_task(_pending_forever(), name="live-usage-trailing-invalidation")
    await asyncio.sleep(0)
    assert live_ingest._ingestor is None

    await suite_conftest._reap_leaked_live_usage_ingestor()

    assert consumer.cancelled()
    assert trailing.cancelled()
    assert suite_conftest._consume_dead_live_ingest_task_failures() == []
    assert suite_conftest._pending_live_ingest_tasks(asyncio.get_running_loop()) == []


async def test_dead_detached_owned_task_exception_is_consumed_without_the_loop() -> None:
    # An ingestor-owned task can die with an exception after the singleton and
    # its task fields are already cleared. asyncio.all_tasks() only returns
    # unfinished tasks, so the pending sweep cannot see it — the weak
    # ownership registry in live_ingest must still surface (and retrieve) the
    # failure, and must do so without running the event loop.
    from tests import conftest as suite_conftest

    async def _boom() -> None:
        raise RuntimeError("late detached failure")

    task = asyncio.create_task(_boom(), name="live-usage-trailing-invalidation")
    live_ingest._owned_tasks.add(task)
    await asyncio.sleep(0)
    assert task.done()
    assert live_ingest._ingestor is None
    assert live_hub._publisher is None
    assert suite_conftest._pending_live_ingest_tasks(asyncio.get_running_loop()) == []

    failures = suite_conftest._consume_dead_live_ingest_task_failures()

    assert failures == ["'live-usage-trailing-invalidation' died with RuntimeError('late detached failure')"]
    assert suite_conftest._consume_dead_live_ingest_task_failures() == []


async def test_ingestor_registers_its_tasks_in_the_ownership_registry() -> None:
    # The registry only protects tests if production task creation actually
    # enrolls both task types.
    ingestor = live_ingest.LiveUsageIngestor(queue_size=1, write_min_interval_seconds=0.0)
    ingestor.start()
    ingestor._last_cache_invalidation = time.monotonic()
    await ingestor._invalidate_caches_throttled()

    assert ingestor._consumer in live_ingest._owned_tasks
    assert ingestor._trailing_invalidation in live_ingest._owned_tasks

    await ingestor.stop()
