from __future__ import annotations

import json

import pytest

from app.dependencies import get_proxy_service_for_app
from app.modules.proxy._service.http_bridge import quarantine
from tests.integration.test_http_responses_bridge import (
    _cleanup_http_bridge_sessions as cleanup_http_bridge_sessions,  # noqa: F401
)
from tests.integration.test_http_responses_bridge import (
    _collect_sse_events,
    _promotion_history,
)
from tests.integration.test_http_responses_bridge import (
    promotion_transport as promotion_transport,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("poison", [False, True], ids=["weaker", "poison"])
async def test_promoted_history_quarantine_opens_fresh_without_injecting_an_anchor(
    async_client, app_instance, promotion_transport, poison
):
    upstreams, raw_calls, _ = promotion_transport
    history = _promotion_history()
    body = {"model": "gpt-5.4", "instructions": "test", "stream": True, "input": history}
    first = await _collect_sse_events(async_client, "/v1/responses", json_body=body)
    assert first[-1]["type"] == "response.completed"
    service = get_proxy_service_for_app(app_instance)
    assert len(service._http_bridge_sessions) == 1
    original = next(iter(service._http_bridge_sessions.values()))
    assert original.key.strength == "soft"
    assert original.key.affinity_key.startswith("http-history:")
    reason = (
        quarantine._HTTP_BRIDGE_QUARANTINE_POISONED_ANCHOR_REASON
        if poison
        else quarantine._HTTP_BRIDGE_QUARANTINE_WEDGED_REATTACH_REASON
    )
    assert quarantine._quarantine_http_bridge_session(service, original, reason=reason)
    assert quarantine._http_bridge_session_key_quarantined(service, original.key)

    followup = [*history, {"role": "assistant", "content": "OK"}, {"role": "user", "content": "next"}]
    second = await _collect_sse_events(async_client, "/v1/responses", json_body={**body, "input": followup})
    assert second[-1]["type"] == "response.completed"
    assert not raw_calls
    assert len(upstreams) == 2
    assert service._http_bridge_sessions[original.key] is not original
    assert len(upstreams[0].sent_text) == 1
    frame = json.loads(upstreams[1].sent_text[0])
    assert frame["input"] == [
        history[0],
        {"role": "assistant", "content": [{"type": "output_text", "text": "first answer"}]},
        history[2],
        {"role": "assistant", "content": [{"type": "output_text", "text": "OK"}]},
        followup[-1],
    ]
    assert "previous_response_id" not in frame
