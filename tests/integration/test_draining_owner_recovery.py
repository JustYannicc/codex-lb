from __future__ import annotations

import asyncio
import time
from collections import deque
from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import anyio
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from sqlalchemy import select

from app.core.config.settings import Settings
from app.db.models import ApiKeyLimit, ApiKeyUsageReservation
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyCreateData, ApiKeysService, LimitRuleInput
from app.modules.proxy import service as proxy_service
from app.modules.proxy.http_bridge_forwarding import (
    HTTP_BRIDGE_INTERNAL_FORWARD_PATH,
    HTTP_BRIDGE_RESERVATION_ID_HEADER,
    HTTPBridgeOwnerClient,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("release_fails", [False, True])
@pytest.mark.parametrize("file_pinned", [False, True])
async def test_draining_owner_releases_admission_before_local_retry(
    monkeypatch, tmp_path, db_setup, release_fails, file_pinned
):
    """A real non-200 owner response must return the single reservation slot."""
    monkeypatch.setenv("CODEX_LB_ENCRYPTION_KEY_FILE", str(tmp_path / "bridge.key"))
    service = proxy_service.ProxyService(cast(Any, nullcontext()))
    turn_state = "http_turn_drain_reservation"
    async with SessionLocal() as session:
        key_service = ApiKeysService(ApiKeysRepository(session))
        api_key = await key_service.create_key(
            ApiKeyCreateData(
                name="drain-reservation",
                allowed_models=None,
                expires_at=None,
                limits=[LimitRuleInput(limit_type="total_tokens", limit_window="weekly", max_value=1)],
            )
        )
        original = await key_service.enforce_limits_for_request(api_key.id, request_model="gpt-5.4")
        assert original is not None
    key = proxy_service._HTTPBridgeSessionKey("turn_state_header", turn_state, api_key.id)
    retry = None
    transitions = []

    async def reject_owner(request):
        assert request.headers[HTTP_BRIDGE_RESERVATION_ID_HEADER] == original.reservation_id
        assert (await request.json())["model"] == "gpt-5.4"
        transitions.append("owner-rejected")
        return web.json_response(
            {"error": {"code": "bridge_drain_active", "message": "Owner draining", "type": "server_error"}},
            status=503,
        )

    async def release(reservation):
        if reservation is not None:
            if release_fails and reservation.reservation_id == original.reservation_id:
                raise RuntimeError("reservation store unavailable")
            async with SessionLocal() as session:
                await ApiKeysService(ApiKeysRepository(session)).release_usage_reservation(reservation.reservation_id)
            transitions.append("release:original" if reservation == original else "release:retry")

    async def reserve(key, **kwargs):
        nonlocal retry
        transitions.append("reserve:retry")
        async with SessionLocal() as session:
            retry = await ApiKeysService(ApiKeysRepository(session)).enforce_limits_for_request(key.id, **kwargs)
        assert retry is not None
        assert retry.reservation_id != original.reservation_id
        return retry

    def prepare(payload, headers, *, api_key, api_key_reservation, request_id, client_ip=None):
        state = proxy_service._WebSocketRequestState(
            request_id=request_id,
            model=payload.model,
            service_tier=None,
            reasoning_effort=None,
            api_key_reservation=api_key_reservation,
            started_at=time.monotonic(),
            event_queue=asyncio.Queue(),
            transport="http",
        )
        return state, '{"type":"response.create"}'

    async def local_events(session, *, request_state, **kwargs):
        assert request_state.api_key_reservation is retry
        await service._release_websocket_request_state_reservation(request_state)
        yield 'data: {"type":"response.completed"}\n\n'

    recovery_session = proxy_service._HTTPBridgeSession(
        key=key,
        headers={"x-codex-turn-state": turn_state},
        affinity=proxy_service._AffinityPolicy(key=turn_state, kind=proxy_service.StickySessionKind.CODEX_SESSION),
        request_model="gpt-5.4",
        account=cast(Any, SimpleNamespace(id="acc-local")),
        upstream=cast(Any, SimpleNamespace(close=AsyncMock())),
        upstream_control=proxy_service._WebSocketUpstreamControl(),
        pending_requests=deque(),
        pending_lock=anyio.Lock(),
        response_create_gate=asyncio.Semaphore(1),
        queued_request_count=0,
        last_used_at=time.monotonic(),
        idle_ttl_seconds=120.0,
    )
    monkeypatch.setattr(proxy_service, "get_settings", lambda: Settings(http_responses_session_bridge_enabled=True))
    monkeypatch.setattr(
        proxy_service,
        "get_settings_cache",
        lambda: SimpleNamespace(
            get=AsyncMock(
                return_value=SimpleNamespace(
                    sticky_threads_enabled=False,
                    openai_cache_affinity_max_age_seconds=1800,
                    http_responses_session_bridge_prompt_cache_idle_ttl_seconds=3600,
                    http_responses_session_bridge_gateway_safe_mode=False,
                )
            )
        ),
    )
    monkeypatch.setattr(service._durable_bridge, "lookup_request_targets", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_prepare_http_bridge_request", prepare)
    monkeypatch.setattr(service, "_http_bridge_owner_client", HTTPBridgeOwnerClient())
    monkeypatch.setattr(service, "_release_websocket_reservation", release)
    monkeypatch.setattr(service, "_reserve_websocket_api_key_usage", reserve)
    monkeypatch.setattr(service, "_stream_http_bridge_session_events", local_events)
    monkeypatch.setattr(service, "_detach_http_bridge_request", AsyncMock())

    owner_app = web.Application()
    owner_app.router.add_post(HTTP_BRIDGE_INTERNAL_FORWARD_PATH, reject_owner)
    async with TestServer(owner_app) as owner_server:
        owner = proxy_service._HTTPBridgeOwnerForward(
            owner_instance="instance-b",
            owner_endpoint=str(owner_server.make_url("")).rstrip("/"),
            key=key,
        )
        get_or_create = AsyncMock(side_effect=[owner, recovery_session])
        monkeypatch.setattr(service, "_get_or_create_http_bridge_session", get_or_create)
        stream = service._stream_via_http_bridge(
            proxy_service.ResponsesRequest.model_validate({"model": "gpt-5.4", "instructions": "hi", "input": "hi"}),
            headers={"x-codex-turn-state": turn_state},
            codex_session_affinity=True,
            propagate_http_errors=True,
            openai_cache_affinity=False,
            api_key=api_key,
            api_key_reservation=original,
            suppress_text_done_events=False,
            idle_ttl_seconds=120.0,
            codex_idle_ttl_seconds=900.0,
            max_sessions=8,
            queue_limit=4,
            downstream_turn_state=turn_state,
            rewritten_file_account_id="acc-local" if file_pinned else None,
        )
        if release_fails:
            with pytest.raises(RuntimeError, match="reservation store unavailable"):
                async for _ in stream:
                    pass
            assert transitions == ["owner-rejected"]
            assert get_or_create.await_count == 1
            async with SessionLocal() as session:
                reservations = (await session.scalars(select(ApiKeyUsageReservation))).all()
                assert len(reservations) == 1
                assert reservations[0].id == original.reservation_id
                assert reservations[0].status == "reserved"
            return
        chunks = [chunk async for chunk in stream]
    assert chunks == ['data: {"type":"response.completed"}\n\n']
    assert transitions == ["owner-rejected", "release:original", "reserve:retry", "release:retry"]
    async with SessionLocal() as session:
        reservations = (await session.scalars(select(ApiKeyUsageReservation))).all()
        assert len(reservations) == 2
        assert {row.status for row in reservations} == {"released"}
        limit = (await session.scalars(select(ApiKeyLimit))).one()
        assert limit.current_value == 0
    assert get_or_create.await_args_list[1].kwargs["allow_bootstrap_owner_rebind"] is True

    if file_pinned:
        assert get_or_create.await_args_list[1].kwargs["preferred_account_id"] == "acc-local"
