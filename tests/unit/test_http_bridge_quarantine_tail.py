from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.http_bridge import quarantine
from tests.simulation.virtual_time import VirtualClock
from tests.unit.test_proxy_http_bridge import _make_bridge_session, _make_eventless_http_bridge_owner


@pytest.mark.asyncio
@pytest.mark.parametrize("completion_time", [1600.0, 1601.0], ids=["at-expiry", "after-expiry"])
@pytest.mark.parametrize("race", [None, "weaker", "poison", "first-strike"])
@pytest.mark.parametrize("durable_miss", [False, True], ids=["local", "overflow-durable-miss"])
async def test_healthy_completion_clears_observed_weaker_tail_but_preserves_new_evidence(
    monkeypatch: pytest.MonkeyPatch,
    completion_time: float,
    race: str | None,
    durable_miss: bool,
) -> None:
    clock = VirtualClock(monotonic_value=1000.0)
    service = proxy_service.ProxyService(Mock(), clock=clock)
    session = _make_bridge_session(key_value="late-weaker-tail")
    service._http_bridge_sessions[session.key] = session
    quarantine._quarantine_http_bridge_session(
        service, session, reason=quarantine._HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
    )
    clock.advance(500.0)
    quarantine._quarantine_http_bridge_session(
        service, session, reason=quarantine._HTTP_BRIDGE_QUARANTINE_WEDGED_REATTACH_REASON
    )
    clock.advance(completion_time - 1500.0)
    entry = quarantine._http_bridge_quarantine_registry(service)[session.key]
    assert entry.poison_quarantined_until == 1600.0
    assert entry.quarantined_until == 2100.0
    assert not quarantine._http_bridge_session_key_poison_quarantined(service, session.key)
    observed_generation = entry.generation
    fence = quarantine._http_bridge_quarantine_clear_fence_details(service, session.key)
    assert fence.generation == observed_generation
    assert fence.raw_generation == observed_generation
    newer_generation = None

    async def register(*_args: object, **_kwargs: object) -> bool:
        nonlocal newer_generation
        # Production captures its fence before awaiting anchor registration.
        # A new arm here must survive the later completion cleanup.
        if race == "first-strike":
            quarantine._record_http_bridge_quarantine_eventless_timeout(service, session)
        elif race is not None:
            reason = (
                quarantine._HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
                if race == "poison"
                else quarantine._HTTP_BRIDGE_QUARANTINE_WEDGED_REATTACH_REASON
            )
            quarantine._quarantine_http_bridge_session(service, session, reason=reason)
        if race is not None:
            newer_generation = quarantine._http_bridge_quarantine_registry(service)[session.key].generation
        return True

    service._register_http_bridge_previous_response_id = AsyncMock(side_effect=register)
    service._maybe_release_idle_http_bridge_session_lease = AsyncMock()
    service._write_request_log = AsyncMock()
    service._handle_stream_error = AsyncMock()
    service._durable_bridge = None
    durable_lookup = AsyncMock(return_value=None)
    persisted_keys = {session.key}
    if durable_miss:
        service._durable_bridge = Mock(lookup_retry_circuit=durable_lookup)
        monkeypatch.setattr(service, "_http_bridge_retry_circuit_persisted_keys", persisted_keys)
        monkeypatch.setattr(service, "_http_bridge_quarantine_poison_overflow_until", 2200.0, raising=False)
        assert quarantine._http_bridge_session_key_poison_quarantined(service, session.key)
    else:
        service._load_http_bridge_retry_circuit = AsyncMock()
    service._clear_http_bridge_retry_circuit = AsyncMock(return_value=True)
    owner = _make_eventless_http_bridge_owner(request_id="req-late-weaker")
    owner.event_queue = asyncio.Queue()
    owner.awaiting_response_created = True
    session.pending_requests.append(owner)
    session.queued_request_count = 1
    await service._process_http_bridge_upstream_text(
        session, '{"type":"response.completed","response":{"id":"resp_late"}}'
    )
    service._register_http_bridge_previous_response_id.assert_awaited_once()
    if durable_miss:
        durable_lookup.assert_awaited_once()
        assert session.key not in persisted_keys
        expected_overflow = max(2200.0, completion_time + 600.0) if race == "poison" else 2200.0
        assert quarantine._http_bridge_quarantine_poison_overflow_until(service, clock.monotonic()) == expected_overflow
    after = quarantine._http_bridge_quarantine_registry(service).get(session.key)
    if race is None:
        assert after is None
        assert not session.quarantined
        assert not quarantine._http_bridge_session_key_quarantined(service, session.key)
    else:
        assert after is not None
        assert newer_generation is not None and newer_generation > observed_generation
        assert after.generation == newer_generation
        assert session.quarantined
        if race == "first-strike":
            assert after.consecutive_eventless_timeouts == 1
