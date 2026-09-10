from __future__ import annotations

import pytest
from aiohttp import web

from tests.integration.model_source_helpers import stub_source_upstreams

pytestmark = pytest.mark.integration


@pytest.fixture
async def cpa_upstream():
    async with stub_source_upstreams() as start:
        yield start


@pytest.mark.asyncio
async def test_cpa_source_discovers_models_without_manual_registration(async_client, cpa_upstream):
    async def catalog(request: web.Request) -> web.Response:
        assert request.path == "/v1/models"
        assert request.query["client_version"] == "0.144.0"
        assert request.headers["Authorization"] == "Bearer fixture-cpa-key"
        return web.json_response(
            {
                "models": [
                    {
                        "slug": "fixture-claude",
                        "display_name": "Fixture Claude",
                        "context_window": 200000,
                        "max_tokens": 8192,
                        "input_modalities": ["text", "image"],
                        "supports_parallel_tool_calls": True,
                        "supported_reasoning_levels": [{"effort": "high", "description": "High"}],
                        "default_reasoning_level": "high",
                    }
                ]
            }
        )

    base_url = await cpa_upstream(catalog)
    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": base_url,
            "apiKey": "fixture-cpa-key",
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    assert created.json()["catalogMode"] == "cli_proxy_api"
    listed = await async_client.get("/v1/models")
    assert listed.status_code == 200
    entry = next(item for item in listed.json()["data"] if item["id"] == "fixture-claude")
    assert entry["context_length"] == 200000
    codex = await async_client.get("/backend-api/codex/models", params={"client_version": "0.144.0"})
    assert codex.status_code == 200
    entry = next(item for item in codex.json()["models"] if item["slug"] == "fixture-claude")
    assert entry["input_modalities"] == ["text", "image"]
    assert entry["default_reasoning_level"] == "high"
    assert entry["supported_reasoning_levels"] == [{"effort": "high", "description": "High"}]


@pytest.mark.asyncio
async def test_cpa_preserves_reported_metadata_without_template_fallback(async_client, cpa_upstream):
    async def catalog(request):
        return web.json_response(
            {
                "models": [
                    {
                        "slug": "fixture-audio",
                        "description": "Reported description",
                        "context_window": 65536,
                        "max_tokens": 2048,
                        "input_modalities": ["text", "audio"],
                        "support_verbosity": True,
                        "default_verbosity": "low",
                    }
                ]
            }
        )

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    response = await async_client.get("/backend-api/codex/models")
    entry = next(item for item in response.json()["models"] if item["slug"] == "fixture-audio")
    assert entry["description"] == "Reported description"
    assert entry["input_modalities"] == ["text", "audio"]
    assert entry["support_verbosity"] is True
    assert entry["default_verbosity"] == "low"
    assert entry["supported_reasoning_levels"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["status", "auth", "invalid_json", "invalid_model", "duplicate", "oversize"])
async def test_cpa_failed_refresh_keeps_durable_catalog(async_client, cpa_upstream, monkeypatch, failure):
    from datetime import timedelta

    from app.modules.model_sources import discovery

    now = discovery.utcnow()
    monkeypatch.setattr(discovery, "utcnow", lambda: now)
    failing = False

    async def catalog(request):
        if not failing:
            return web.json_response({"models": [{"slug": "fixture-retained", "context_window": 12345}]})
        if failure == "status":
            return web.Response(status=503)
        if failure == "auth":
            return web.Response(status=401)
        if failure == "invalid_json":
            return web.Response(text="broken")
        if failure == "invalid_model":
            return web.json_response({"models": [{"slug": "new-model"}, {"slug": "broken", "context_window": "bad"}]})
        if failure == "duplicate":
            return web.json_response({"models": [{"slug": "same"}, {"slug": "same"}]})
        return web.Response(body=b" " * (2 * 1024 * 1024 + 1))

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    initial = await async_client.get("/v1/models")
    assert any(item["id"] == "fixture-retained" for item in initial.json()["data"])
    failing = True
    now += timedelta(seconds=61)
    listed = await async_client.get("/v1/models")
    assert any(item["id"] == "fixture-retained" for item in listed.json()["data"])
    assert all(item["id"] != "new-model" for item in listed.json()["data"])
    sources = await async_client.get("/api/model-sources/")
    row = sources.json()["sources"][0]["models"][0]
    assert row["model"] == "fixture-retained"
    assert row["contextWindow"] == 12345
    assert row["isEnabled"] is True


@pytest.mark.asyncio
async def test_cpa_omission_rejects_requests_and_return_preserves_identity(async_client, cpa_upstream, monkeypatch):
    from datetime import timedelta

    from app.modules.model_sources import discovery

    now = discovery.utcnow()
    monkeypatch.setattr(discovery, "utcnow", lambda: now)
    models = [{"slug": "fixture-returning"}]

    async def catalog(request):
        assert request.method == "GET"
        return web.json_response({"models": models})

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    await async_client.get("/v1/models")
    source = (await async_client.get("/api/model-sources/")).json()["sources"][0]
    identity = source["models"][0]["id"]
    models = []
    now += timedelta(seconds=61)
    listed = await async_client.get("/v1/models")
    assert all(item["id"] != "fixture-returning" for item in listed.json()["data"])
    response = await async_client.post("/v1/responses", json={"model": "fixture-returning", "input": "hello"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_source_disabled"
    models = [{"slug": "fixture-returning"}]
    now += timedelta(seconds=61)
    listed = await async_client.get("/v1/models")
    assert any(item["id"] == "fixture-returning" for item in listed.json()["data"])
    source = (await async_client.get("/api/model-sources/")).json()["sources"][0]
    assert source["models"][0]["id"] == identity
    assert source["models"][0]["isEnabled"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("edit", ["disable", "manual", "delete", "url"])
async def test_cpa_inflight_refresh_cannot_override_configuration(async_client, cpa_upstream, edit):
    import asyncio

    entered = asyncio.Event()
    release = asyncio.Event()

    async def catalog(request):
        entered.set()
        await release.wait()
        return web.json_response({"models": [{"slug": "stale-acquisition"}]})

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    source_id = created.json()["id"]
    pending = asyncio.create_task(async_client.get("/v1/models"))
    try:
        await asyncio.wait_for(entered.wait(), timeout=3)
        if edit == "delete":
            changed = await async_client.delete(f"/api/model-sources/{source_id}")
            assert changed.status_code == 204
        else:
            payload = {
                "disable": {"isEnabled": False},
                "manual": {"catalogMode": "manual"},
                "url": {"baseUrl": "http://127.0.0.1:1/v1"},
            }[edit]
            changed = await async_client.patch(f"/api/model-sources/{source_id}", json=payload)
            assert changed.status_code == 200
    finally:
        release.set()
        listed = await pending
    assert all(item["id"] != "stale-acquisition" for item in listed.json()["data"])
    sources = (await async_client.get("/api/model-sources/")).json()["sources"]
    assert not sources or sources[0]["models"] == []


@pytest.mark.asyncio
async def test_concurrent_catalog_reads_share_refresh_and_keep_cadence(async_client, cpa_upstream):
    import asyncio

    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def catalog(request):
        calls.append(request.path)
        entered.set()
        await release.wait()
        return web.json_response({"models": [{"slug": "fixture-single-refresh"}]})

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    pending = asyncio.create_task(async_client.get("/v1/models"))
    try:
        await asyncio.wait_for(entered.wait(), timeout=3)
        other = await async_client.get("/v1/models")
        assert other.status_code == 200
    finally:
        release.set()
        await pending
    listed = await async_client.get("/v1/models")
    assert any(item["id"] == "fixture-single-refresh" for item in listed.json()["data"])
    assert calls == ["/v1/models"]


@pytest.mark.asyncio
async def test_cpa_catalog_cannot_be_replaced_by_manual_model_update(async_client, cpa_upstream):
    async def catalog(request):
        return web.json_response({"models": [{"slug": "fixture-owned"}]})

    created = await async_client.post(
        "/api/model-sources/",
        json={
            "name": "CPA",
            "baseUrl": await cpa_upstream(catalog),
            "catalogMode": "cli_proxy_api",
            "supportsResponses": True,
        },
    )
    assert created.status_code == 200
    await async_client.get("/v1/models")
    response = await async_client.patch(f"/api/model-sources/{created.json()['id']}", json={"models": []})
    assert response.status_code == 400
    listed = await async_client.get("/v1/models")
    assert any(item["id"] == "fixture-owned" for item in listed.json()["data"])
