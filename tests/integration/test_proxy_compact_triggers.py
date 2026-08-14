from __future__ import annotations

import base64
import json
from typing import cast

import pytest

import app.modules.proxy.service as proxy_module
from app.core.openai.models import CompactResponsePayload

pytestmark = pytest.mark.integration


def _encode_jwt(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"header.{body}.sig"


def _make_auth_json(account_id: str, email: str, *, plan_type: str = "plus") -> dict:
    payload = {
        "email": email,
        "chatgpt_account_id": account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": plan_type},
    }
    return {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access-token",
            "refreshToken": "refresh-token",
            "accountId": account_id,
        },
    }


@pytest.mark.asyncio
async def test_proxy_compact_rejects_duplicate_compaction_trigger_before_upstream(async_client, monkeypatch):
    email = "compact-duplicate-trigger@example.com"
    raw_account_id = "acc_compact_duplicate_trigger"
    auth_json = _make_auth_json(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    async def fake_compact(*args, **kwargs):
        del args, kwargs
        pytest.fail("compact should not be called when input contains duplicate compaction_trigger items")

    monkeypatch.setattr(proxy_module, "core_compact_responses", fake_compact)

    response = await async_client.post(
        "/backend-api/codex/responses/compact",
        json={
            "model": "gpt-5.1",
            "instructions": "hi",
            "input": [
                {"role": "user", "content": "hello"},
                {"type": "compaction_trigger"},
                {"type": "compaction_trigger"},
            ],
        },
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"
    assert error["code"] == "invalid_request_error"
    assert error["param"] == "input"


@pytest.mark.asyncio
async def test_proxy_compact_rejects_non_terminal_compaction_trigger_before_instruction_hoist(
    async_client,
    monkeypatch,
):
    email = "compact-trigger-hoist@example.com"
    raw_account_id = "acc_compact_trigger_hoist"
    auth_json = _make_auth_json(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    async def fake_compact(*args, **kwargs):
        del args, kwargs
        pytest.fail("compact should not be called when a trailing developer message hides a non-terminal trigger")

    monkeypatch.setattr(proxy_module, "core_compact_responses", fake_compact)

    response = await async_client.post(
        "/backend-api/codex/responses/compact",
        json={
            "model": "gpt-5.1",
            "instructions": "",
            "input": [
                {"role": "user", "content": "hello"},
                {"type": "compaction_trigger"},
                {"role": "developer", "content": "still trailing after the trigger"},
            ],
        },
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["type"] == "invalid_request_error"
    assert error["code"] == "invalid_request_error"
    assert error["param"] == "input"


@pytest.mark.asyncio
async def test_proxy_compact_preserves_single_terminal_compaction_trigger(async_client, monkeypatch):
    email = "compact-single-trigger@example.com"
    raw_account_id = "acc_compact_single_trigger"
    auth_json = _make_auth_json(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    seen_payloads: list[dict[str, object]] = []

    async def fake_compact(payload, headers, access_token, account_id):
        del headers, access_token, account_id
        seen_payloads.append(cast(dict[str, object], payload.to_payload()))
        return CompactResponsePayload.model_validate({"object": "response.compaction", "output": []})

    monkeypatch.setattr(proxy_module, "core_compact_responses", fake_compact)

    response = await async_client.post(
        "/backend-api/codex/responses/compact",
        json={
            "model": "gpt-5.1",
            "instructions": "hi",
            "input": [
                {"role": "user", "content": "hello"},
                {"type": "compaction_trigger"},
            ],
        },
    )

    assert response.status_code == 200
    assert len(seen_payloads) == 1
    assert seen_payloads[0]["input"] == [
        {"role": "user", "content": "hello"},
        {"type": "compaction_trigger"},
    ]


@pytest.mark.asyncio
async def test_v1_proxy_compact_keeps_trigger_handling_unchanged(async_client, monkeypatch):
    email = "v1-compact-trigger-unchanged@example.com"
    raw_account_id = "acc_v1_compact_trigger_unchanged"
    auth_json = _make_auth_json(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    seen_payloads: list[dict[str, object]] = []

    async def fake_compact(payload, headers, access_token, account_id):
        del headers, access_token, account_id
        seen_payloads.append(cast(dict[str, object], payload.to_payload()))
        return CompactResponsePayload.model_validate({"object": "response.compaction", "output": []})

    monkeypatch.setattr(proxy_module, "core_compact_responses", fake_compact)

    response = await async_client.post(
        "/v1/responses/compact",
        json={
            "model": "gpt-5.1",
            "input": [
                {"role": "user", "content": "hello"},
                {"type": "compaction_trigger"},
                {"type": "compaction_trigger"},
            ],
        },
    )

    assert response.status_code == 200
    assert len(seen_payloads) == 1
    assert seen_payloads[0]["input"] == [
        {"role": "user", "content": "hello"},
        {"type": "compaction_trigger"},
    ]
