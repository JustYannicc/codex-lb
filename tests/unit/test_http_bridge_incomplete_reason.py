"""Explicit incomplete reasons preserve circuit and downstream contracts."""

from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.http_bridge import retry_circuit
from tests.unit.test_proxy_http_bridge import _make_terminal_error_bridge_fixture, _stateful_retry_circuit_persistence

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("half_open", [False, True])
@pytest.mark.parametrize(
    "kind", ["stream_reason", "neutral_reason", "explicit_error", "unknown_reason", "missing_reason", "other_error"]
)
async def test_incomplete_reason_preserves_circuit_accounting(
    monkeypatch: pytest.MonkeyPatch, half_open: bool, kind: str
) -> None:
    service, session, request = _make_terminal_error_bridge_fixture(
        request_id="diagnostic-incomplete",
        key_value=f"reason-{kind}-{half_open}",
        response_event_count=0,
    )
    request.started_at = time.monotonic()
    request.bridge_request_deadline = request.started_at + 7200.0
    request.awaiting_response_created = True
    request.response_create_attempt_count = 1
    request.response_create_sent_at = request.started_at
    session.account.chatgpt_account_id = "diagnostic-workspace"
    service._durable_bridge = SimpleNamespace(**_stateful_retry_circuit_persistence())
    handle_error = AsyncMock()
    monkeypatch.setattr(service, "_handle_stream_error", handle_error)
    monkeypatch.setattr(
        proxy_service,
        "get_settings_cache",
        lambda: SimpleNamespace(get=AsyncMock(return_value=proxy_service.get_settings())),
    )
    original_count = 0
    claimed_until = 0.0
    if half_open:
        original_count = 2
        circuit = retry_circuit._HTTPBridgeRetryCircuitState(
            consecutive_failures=2,
            cooldown_until=request.started_at - 1.0,
            last_detail="stream_incomplete",
            last_touched_monotonic=request.started_at,
        )
        cast(Any, service)._http_bridge_retry_circuits[session.key] = circuit
        # Claim the request-bound probe used by production dispatch.
        assert await service._http_bridge_precreated_retry_allowed(session, probe_owner=request)
        request.claimed_half_open_generation = circuit.half_open_lease_generation
        claimed_until = circuit.half_open_until
    reason = {"neutral_reason": "max_output_tokens", "unknown_reason": "unknown_reason"}.get(kind, "stream_incomplete")
    response: dict[str, Any] = {
        "id": "resp-diagnostic",
        "object": "response",
        "status": "incomplete",
        "incomplete_details": {"reason": reason},
    }
    if kind == "explicit_error":
        response["error"] = {"type": "server_error", "code": "stream_incomplete", "message": "stream failed"}
    if kind == "other_error":
        response["error"] = {"type": "invalid_request_error", "code": "permission_denied", "message": "Denied"}
    if kind == "missing_reason":
        response.pop("incomplete_details")
    payload = {"type": "response.incomplete", "response": response}
    processed = asyncio.Event()
    calls = 0

    async def receive() -> UpstreamWebSocketMessage:
        nonlocal calls
        calls += 1
        if calls == 1:
            return UpstreamWebSocketMessage(kind="text", text=json.dumps(payload))
        processed.set()
        await asyncio.Event().wait()
        raise AssertionError("Unreachable")

    monkeypatch.setattr(session.upstream, "receive", receive, raising=False)
    queue = request.event_queue
    assert queue is not None
    reader = asyncio.create_task(service._relay_http_bridge_upstream_messages(session))
    session.upstream_reader = reader
    try:
        await asyncio.wait_for(processed.wait(), timeout=2.0)
        terminal_block = queue.get_nowait()
        assert terminal_block is not None
        terminal = proxy_service.parse_sse_data_json(terminal_block)
        assert terminal is not None and terminal["type"] == "response.incomplete"
        terminal_response = cast(dict[str, Any], terminal["response"])
        assert terminal_response.get("incomplete_details") == response.get("incomplete_details")
        assert terminal_response.get("error") == response.get("error")
        assert queue.get_nowait() is None
        assert not session.pending_requests
        circuit = cast(Any, service)._http_bridge_retry_circuits.get(session.key)
        count = circuit.consecutive_failures if circuit is not None else 0
        lease = circuit.half_open_until if circuit is not None else 0.0
        persisted = service._durable_bridge.persist_retry_circuit.await_count
        if kind not in {"stream_reason", "explicit_error"}:
            assert count == original_count
            assert persisted == 0
            if half_open:
                assert lease == claimed_until
                assert circuit.half_open_owner_token is request
        else:
            assert count == original_count + 1, "Explicit stream_incomplete reason did not consume a circuit strike"
            assert persisted == 1
            if half_open:
                assert lease == 0.0
                assert circuit.half_open_owner_token is None
            # A duplicate terminal cannot charge this physical attempt twice.
            await service._process_http_bridge_upstream_text(session, json.dumps(payload))
            assert circuit.consecutive_failures == count
            assert service._durable_bridge.persist_retry_circuit.await_count == persisted
            assert queue.empty()
        assert request.terminal_settlement_phase is None
        if kind not in {"explicit_error", "other_error"}:
            handle_error.assert_not_awaited()
        if kind in {"stream_reason", "neutral_reason", "unknown_reason"}:
            write_log = cast(AsyncMock, service._write_request_log)
            write_log.assert_awaited_once()
            assert write_log.await_args is not None
            assert write_log.await_args.kwargs["error_code"] == reason
    finally:
        if not reader.done():
            reader.cancel()
        await asyncio.wait_for(asyncio.gather(reader, return_exceptions=True), timeout=2.0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exclusion", ["midstream", "prewarm", "skip_log", "safe_replay", "soft_key", "disarmed", "recorded"]
)
async def test_incomplete_reason_keeps_existing_attempt_exclusions(
    monkeypatch: pytest.MonkeyPatch, exclusion: str
) -> None:
    service, session, request = _make_terminal_error_bridge_fixture(
        request_id="incomplete-excluded", key_value=f"excluded-{exclusion}", response_event_count=0
    )
    request.awaiting_response_created = True
    service._durable_bridge = SimpleNamespace(**_stateful_retry_circuit_persistence())
    handle_error = AsyncMock()
    monkeypatch.setattr(service, "_handle_stream_error", handle_error)
    if exclusion == "midstream":
        request.response_event_count = 1
        request.response_id = "resp-excluded"
    elif exclusion == "prewarm":
        request.request_kind = "prewarm"
    elif exclusion == "skip_log":
        request.skip_request_log = True
    elif exclusion == "safe_replay":
        request.fresh_upstream_request_is_retry_safe = True
        request.fresh_upstream_request_text = '{"type":"response.create","input":"full resend"}'
    elif exclusion == "soft_key":
        session.key = proxy_service._HTTPBridgeSessionKey("prompt_cache", "soft-incomplete", None)
    else:
        assert request.response_create_attempt is not None
        if exclusion == "disarmed":
            request.response_create_attempt.disarmed = True
        else:
            request.response_create_attempt.retry_circuit_failure_recorded = True
    queue = request.event_queue
    assert queue is not None
    await service._process_http_bridge_upstream_text(
        session,
        json.dumps(
            {
                "type": "response.incomplete",
                "response": {
                    "id": "resp-excluded",
                    "status": "incomplete",
                    "incomplete_details": {"reason": "stream_incomplete"},
                },
            }
        ),
    )
    service._durable_bridge.persist_retry_circuit.assert_not_awaited()
    handle_error.assert_not_awaited()
    circuit = cast(Any, service)._http_bridge_retry_circuits.get(session.key)
    assert circuit is None or circuit.consecutive_failures == 0
    terminal_block = queue.get_nowait()
    assert terminal_block is not None
    terminal = proxy_service.parse_sse_data_json(terminal_block)
    assert terminal is not None and terminal["type"] == "response.incomplete"
    assert queue.get_nowait() is None
    assert not session.pending_requests
