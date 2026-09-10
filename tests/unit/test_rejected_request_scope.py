"""Deferred health writes retain the request that was actually rejected."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.modules.proxy.service as proxy_module
from app.db.models import Account
from app.modules.proxy._service.websocket.helpers import _record_or_defer_websocket_accepted_replay_health

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["websocket", "bridge"])
async def test_deferred_rejection_scope_survives_request_state_changes(surface):
    service = proxy_module.ProxyService(MagicMock())
    service._handle_stream_error = AsyncMock()
    account = Account(id="scoped-account")
    request = proxy_module._WebSocketRequestState(
        request_id="scoped-request",
        model="gpt-6-astra",
        service_tier="priority",
        reasoning_effort=None,
        api_key_reservation=MagicMock(),
        started_at=0,
    )
    if surface == "websocket":
        await _record_or_defer_websocket_accepted_replay_health(
            service,
            request,
            account=account,
            error_message="quota reached",
            error_code="usage_limit_reached",
        )
    else:
        await service._handle_or_defer_precreated_stream_health(
            request, account, {"message": "quota reached"}, "usage_limit_reached"
        )
    service._handle_stream_error.assert_not_awaited()
    request.model = "gpt-5.5"
    request.service_tier = None
    await service._drain_deferred_keyed_stream_health(request)
    service._handle_stream_error.assert_awaited_once_with(
        account,
        {"message": "quota reached"},
        "usage_limit_reached",
        rejected_model="gpt-6-astra",
        rejected_service_tier="priority",
    )
    assert request.deferred_keyed_stream_health == []
