from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import anyio
import pytest

from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.http_bridge import request_submit as request_submit_module
from app.modules.proxy._service.http_bridge import upstream_events as upstream_events_module
from app.modules.proxy.http_bridge_event_batcher import TerminalOperationEventAppendResult

pytestmark = pytest.mark.unit


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        http_responses_session_bridge_instance_id="terminal-delivery-test",
        http_responses_session_bridge_operation_event_spool_max_bytes=1024,
        http_responses_session_bridge_request_budget_seconds=60.0,
    )


def _request_state(event_queue: asyncio.Queue[str | None]) -> proxy_service._WebSocketRequestState:
    return proxy_service._WebSocketRequestState(
        request_id="req-terminal-delivery",
        model="gpt-5.6-sol",
        service_tier=None,
        reasoning_effort=None,
        api_key_reservation=None,
        started_at=time.monotonic(),
        event_queue=event_queue,
        event_queue_revoked=cast(Any, event_queue)._revoked,
        operation_id="op-terminal-delivery",
        response_id="resp-terminal-delivery",
        transport="http",
    )


def _session() -> Any:
    return cast(
        Any,
        SimpleNamespace(
            durable_session_id="durable-terminal-delivery",
            durable_owner_epoch=1,
            pending_lock=anyio.Lock(),
        ),
    )


def _live_queue(*, maxsize: int) -> asyncio.Queue[str | None]:
    return request_submit_module._HTTPBridgeLiveEventQueue(maxsize=maxsize, revoked=asyncio.Event())


@pytest.mark.asyncio
async def test_terminal_delivery_times_out_on_full_queue_and_settles(monkeypatch: pytest.MonkeyPatch) -> None:
    queue = _live_queue(maxsize=2)
    queue.put_nowait("buffered-1")
    queue.put_nowait("buffered-2")
    request_state = _request_state(queue)
    monkeypatch.setattr(proxy_service, "get_settings", _settings)
    monkeypatch.setattr(upstream_events_module, "_HTTP_BRIDGE_TERMINAL_DELIVERY_TIMEOUT_SECONDS", 0.02)
    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))
    settle_terminal_event = AsyncMock()
    service._http_bridge_operation_event_batcher = cast(
        Any,
        SimpleNamespace(
            append_terminal_event=AsyncMock(
                return_value=TerminalOperationEventAppendResult(persisted=False, settlement_required=True)
            ),
            settle_terminal_event=settle_terminal_event,
        ),
    )

    started = time.monotonic()
    result = await upstream_events_module._persist_http_bridge_operation_event(
        service,
        _session(),
        request_state,
        'data: {"type":"response.failed"}\n\n',
        terminal=True,
        terminal_state="failed",
        terminal_event_queue=queue,
    )

    assert result is False
    assert time.monotonic() - started < 0.5
    settle_terminal_event.assert_awaited_once()
    assert request_state.terminal_delivery_timed_out is True
    assert request_state.event_queue_revoked.is_set()
    assert [queue.get_nowait(), queue.get_nowait()] == ["buffered-1", "buffered-2"]
    assert not [
        task
        for task in asyncio.all_tasks()
        if task.get_name() in {"http-bridge-terminal-delivery-op-terminal-delivery", "http-bridge-event-put"}
    ]


@pytest.mark.asyncio
async def test_terminal_delivery_keeps_terminal_before_eos_when_queue_has_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _live_queue(maxsize=2)
    request_state = _request_state(queue)
    monkeypatch.setattr(proxy_service, "get_settings", _settings)
    monkeypatch.setattr(upstream_events_module, "_HTTP_BRIDGE_TERMINAL_DELIVERY_TIMEOUT_SECONDS", 0.2)
    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))
    settle_terminal_event = AsyncMock()
    service._http_bridge_operation_event_batcher = cast(
        Any,
        SimpleNamespace(
            append_terminal_event=AsyncMock(
                return_value=TerminalOperationEventAppendResult(persisted=False, settlement_required=True)
            ),
            settle_terminal_event=settle_terminal_event,
        ),
    )

    result = await upstream_events_module._persist_http_bridge_operation_event(
        service,
        _session(),
        request_state,
        'data: {"type":"response.failed"}\n\n',
        terminal=True,
        terminal_state="failed",
        terminal_event_queue=queue,
    )

    assert result is True
    assert [queue.get_nowait(), queue.get_nowait()] == ['data: {"type":"response.failed"}\n\n', None]
    settle_terminal_event.assert_awaited_once()
    assert request_state.terminal_delivery_timed_out is False


@pytest.mark.asyncio
async def test_terminal_delivery_partial_put_is_closed_with_eos_before_settlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _live_queue(maxsize=2)
    queue.put_nowait("buffered")
    request_state = _request_state(queue)
    monkeypatch.setattr(proxy_service, "get_settings", _settings)
    monkeypatch.setattr(upstream_events_module, "_HTTP_BRIDGE_TERMINAL_DELIVERY_TIMEOUT_SECONDS", 0.02)
    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))
    settle_terminal_event = AsyncMock()
    service._http_bridge_operation_event_batcher = cast(
        Any,
        SimpleNamespace(
            append_terminal_event=AsyncMock(
                return_value=TerminalOperationEventAppendResult(persisted=False, settlement_required=True)
            ),
            settle_terminal_event=settle_terminal_event,
        ),
    )

    result = await upstream_events_module._persist_http_bridge_operation_event(
        service,
        _session(),
        request_state,
        'data: {"type":"response.failed"}\n\n',
        terminal=True,
        terminal_state="failed",
        terminal_event_queue=queue,
    )

    assert result is False
    assert [queue.get_nowait(), queue.get_nowait()] == [
        'data: {"type":"response.failed"}\n\n',
        None,
    ]
    settle_terminal_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_terminal_delivery_preserves_cancellation_after_bounded_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = _live_queue(maxsize=1)
    queue.put_nowait("buffered")
    request_state = _request_state(queue)
    monkeypatch.setattr(proxy_service, "get_settings", _settings)
    monkeypatch.setattr(upstream_events_module, "_HTTP_BRIDGE_TERMINAL_DELIVERY_TIMEOUT_SECONDS", 0.02)
    append_started = asyncio.Event()
    release_append = asyncio.Event()

    async def append_terminal_event(**_: Any) -> TerminalOperationEventAppendResult:
        append_started.set()
        await release_append.wait()
        return TerminalOperationEventAppendResult(persisted=False, settlement_required=True)

    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))
    settle_terminal_event = AsyncMock()
    service._http_bridge_operation_event_batcher = cast(
        Any,
        SimpleNamespace(
            append_terminal_event=append_terminal_event,
            settle_terminal_event=settle_terminal_event,
        ),
    )
    persist_task = asyncio.create_task(
        upstream_events_module._persist_http_bridge_operation_event(
            service,
            _session(),
            request_state,
            'data: {"type":"response.failed"}\n\n',
            terminal=True,
            terminal_state="failed",
            terminal_event_queue=queue,
        )
    )

    await asyncio.wait_for(append_started.wait(), timeout=1.0)
    persist_task.cancel()
    release_append.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(persist_task, timeout=1.0)
    settle_terminal_event.assert_awaited_once()
    assert request_state.terminal_delivery_timed_out is True
