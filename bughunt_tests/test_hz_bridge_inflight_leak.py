from __future__ import annotations

import asyncio
import os
import tempfile
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import anyio
import pytest

_DB_DIR = Path(tempfile.mkdtemp(prefix="codex-lb-bughunt-"))
os.environ.setdefault("CODEX_LB_DATABASE_URL", f"sqlite+aiosqlite:///{_DB_DIR / 'codex-lb.db'}")
os.environ.setdefault("CODEX_LB_UPSTREAM_BASE_URL", "https://example.invalid/backend-api")

import app.modules.proxy.service as proxy_service  # noqa: E402
from app.db.models import Account, AccountStatus  # noqa: E402

pytestmark = pytest.mark.asyncio


def _make_session(key: proxy_service._HTTPBridgeSessionKey) -> proxy_service._HTTPBridgeSession:
    async def _close() -> None:
        return None

    return proxy_service._HTTPBridgeSession(
        key=key,
        headers={},
        affinity=proxy_service._AffinityPolicy(),
        request_model="gpt-5.4",
        account=cast(Account, SimpleNamespace(id="acc-bughunt", status=AccountStatus.ACTIVE, plan_type="plus")),
        upstream=cast(proxy_service.UpstreamWebSocket, SimpleNamespace(close=_close)),
        upstream_control=proxy_service._WebSocketUpstreamControl(),
        pending_lock=anyio.Lock(),
        pending_requests=deque(),
        response_create_gate=asyncio.Semaphore(1),
        queued_request_count=0,
        last_used_at=time.monotonic(),
        idle_ttl_seconds=120.0,
    )


async def test_previous_response_reuse_does_not_leak_inflight_creation_future(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reusing a live session via previous_response_id must not publish an
    orphaned inflight-creation future for that session's key."""

    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))

    response_id = "resp_bughunt_prev_owner"
    owner_key = proxy_service._HTTPBridgeSessionKey("prompt_cache", "bughunt-prev-owner", None)
    owner_session = _make_session(owner_key)
    owner_session.previous_response_ids.add(response_id)
    service._http_bridge_sessions[owner_key] = owner_session
    service._http_bridge_previous_response_index[(response_id, None)] = owner_key

    async def _must_not_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no new bridge session must be created for a reusable previous_response_id")

    monkeypatch.setattr(proxy_service.ProxyService, "_create_http_bridge_session", _must_not_create)

    returned = await service._get_or_create_http_bridge_session(
        proxy_service._HTTPBridgeSessionKey("request", "bughunt-fresh-request", None),
        headers={},
        affinity=proxy_service._AffinityPolicy(),
        api_key=None,
        request_model="gpt-5.4",
        idle_ttl_seconds=120.0,
        max_sessions=128,
        previous_response_id=response_id,
    )

    assert returned is owner_session
    leaked = {key: future for key, future in service._http_bridge_inflight_sessions.items() if not future.done()}
    assert leaked == {}, f"leaked unresolved inflight creation futures: {leaked}"


async def test_leaked_inflight_future_blocks_the_next_request_on_the_same_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second request on the same previous_response_id must still reuse the
    live session instead of tripping over the leaked creation future."""

    service = proxy_service.ProxyService(cast(Any, SimpleNamespace()))

    response_id = "resp_bughunt_prev_owner_2"
    owner_key = proxy_service._HTTPBridgeSessionKey("prompt_cache", "bughunt-prev-owner-2", None)
    owner_session = _make_session(owner_key)
    owner_session.previous_response_ids.add(response_id)
    service._http_bridge_sessions[owner_key] = owner_session
    service._http_bridge_previous_response_index[(response_id, None)] = owner_key

    async def _must_not_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no new bridge session must be created for a reusable previous_response_id")

    monkeypatch.setattr(proxy_service.ProxyService, "_create_http_bridge_session", _must_not_create)

    kwargs: dict[str, Any] = dict(
        headers={},
        affinity=proxy_service._AffinityPolicy(),
        api_key=None,
        request_model="gpt-5.4",
        idle_ttl_seconds=120.0,
        max_sessions=128,
        previous_response_id=response_id,
    )

    first = await service._get_or_create_http_bridge_session(
        proxy_service._HTTPBridgeSessionKey("request", "bughunt-fresh-request-a", None),
        **kwargs,
    )
    assert first is owner_session

    second = await service._get_or_create_http_bridge_session(
        proxy_service._HTTPBridgeSessionKey("request", "bughunt-fresh-request-b", None),
        **kwargs,
    )
    assert second is owner_session
