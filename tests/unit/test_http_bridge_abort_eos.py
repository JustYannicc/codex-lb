from __future__ import annotations

import asyncio
from collections import deque
from types import SimpleNamespace
from typing import Any, cast

import anyio
import pytest

from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.http_bridge import upstream_events as http_bridge_upstream_events

pytestmark = pytest.mark.unit


class _AbortEosService(http_bridge_upstream_events._HTTPBridgeUpstreamEventsMixin):
    def _cancel_request_state_api_key_reservation_heartbeat(
        self,
        request_state: proxy_service._WebSocketRequestState,
    ) -> None:
        del request_state

    async def _release_websocket_request_state_reservation(
        self,
        request_state: proxy_service._WebSocketRequestState,
    ) -> None:
        del request_state


def _make_session() -> proxy_service._HTTPBridgeSession:
    return proxy_service._HTTPBridgeSession(
        key=proxy_service._HTTPBridgeSessionKey("session_header", "sid-abort-eos", None),
        headers={},
        affinity=proxy_service._AffinityPolicy(
            key="sid-abort-eos",
            kind=proxy_service.StickySessionKind.CODEX_SESSION,
        ),
        request_model="gpt-5.5",
        account=cast(Any, SimpleNamespace(id="acc-abort-eos")),
        upstream=cast(Any, SimpleNamespace()),
        upstream_control=proxy_service._WebSocketUpstreamControl(),
        pending_requests=deque(),
        pending_lock=anyio.Lock(),
        response_create_gate=asyncio.Semaphore(1),
        queued_request_count=0,
        last_used_at=0.0,
        idle_ttl_seconds=60.0,
    )


def _make_claimed_request_state(event_queue: asyncio.Queue[str | None]) -> proxy_service._WebSocketRequestState:
    return proxy_service._WebSocketRequestState(
        request_id="req-abort-eos",
        model="gpt-5.5",
        service_tier=None,
        reasoning_effort=None,
        api_key_reservation=None,
        started_at=0.0,
        event_queue=event_queue,
        terminal_settlement_phase="claimed",
        transport="http",
    )


@pytest.mark.asyncio
async def test_aborted_terminal_settlement_unblocks_full_live_queue() -> None:
    """An aborted terminal owner must publish EOS even when the live queue is full."""
    event_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=2)
    event_queue.put_nowait("first-buffered-event")
    event_queue.put_nowait("last-buffered-event")
    assert event_queue.full()
    request_state = _make_claimed_request_state(event_queue)

    await asyncio.wait_for(
        _AbortEosService()._settle_aborted_http_bridge_terminal_states(
            _make_session(),
            [request_state],
        ),
        timeout=0.1,
    )

    # The aborted response is fail-closed: retain the newest buffered event,
    # then terminate immediately instead of waiting for stream idle timeout.
    assert [event_queue.get_nowait(), event_queue.get_nowait()] == ["last-buffered-event", None]
    assert request_state.terminal_settlement_phase is None
    assert not [
        task for task in asyncio.all_tasks() if task.get_name() in {"http-bridge-event-put", "http-bridge-event-revoke"}
    ]


def test_abort_eos_respects_queue_revocation() -> None:
    event_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=1)
    event_queue.put_nowait("buffered-event")
    request_state = _make_claimed_request_state(event_queue)
    request_state.event_queue_revoked.set()

    assert http_bridge_upstream_events._enqueue_http_bridge_abort_eos(request_state, event_queue) is False
    assert event_queue.get_nowait() == "buffered-event"
    assert event_queue.empty()
