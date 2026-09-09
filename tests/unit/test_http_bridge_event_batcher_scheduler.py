from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.proxy.http_bridge_event_batcher import HttpBridgeOperationEventBatcher
from tests.simulation.virtual_time import VirtualClock, VirtualScheduler


@pytest.mark.asyncio
async def test_batcher_owns_flusher_on_injected_scheduler() -> None:
    clock = VirtualClock()
    scheduler = VirtualScheduler(clock)
    durable = SimpleNamespace(append_operation_events=AsyncMock(return_value=True))
    batcher = HttpBridgeOperationEventBatcher(durable, max_bytes=1024, scheduler=scheduler)

    await batcher.enqueue(
        operation_id="operation",
        session_id="session",
        instance_id="instance",
        owner_epoch=1,
        event_text="data: {}\n\n",
    )
    assert any(task.get_name() == "http-bridge-operation-event-flusher" for task in scheduler.owned_tasks)

    await batcher.close()
    await scheduler.drain()

    assert scheduler.owned_tasks == frozenset()
