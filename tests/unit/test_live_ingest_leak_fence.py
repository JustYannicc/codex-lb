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
