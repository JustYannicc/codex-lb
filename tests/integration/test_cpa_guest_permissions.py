"""Real guest sessions keep CPA management read-only across revocation."""

from __future__ import annotations

import pytest
from aiohttp import web
from httpx import ASGITransport, AsyncClient

from tests.integration.model_source_helpers import stub_source_upstreams

pytestmark = pytest.mark.integration


async def test_guest_cannot_change_cpa_source_and_revocation_preserves_public_catalog(app_instance):
    async def catalog(request):
        assert request.headers["Authorization"] == "Bearer fixture-cpa-key"
        return web.json_response({"models": [{"slug": "guest-compatible-cpa", "context_window": 8192}]})

    admin_transport = ASGITransport(app=app_instance, client=("127.0.0.1", 50000))
    guest_transport = ASGITransport(app=app_instance, client=("203.0.113.31", 50001))
    async with app_instance.router.lifespan_context(app_instance), stub_source_upstreams() as start:
        async with (
            AsyncClient(transport=admin_transport, base_url="http://localhost") as admin,
            AsyncClient(transport=guest_transport, base_url="http://lb.example") as guest,
        ):
            native = (await admin.get("/v1/models")).json()["data"]
            settings = (await admin.get("/api/settings")).json()
            settings["guestAccessEnabled"] = True
            assert (await admin.put("/api/settings", json=settings)).status_code == 200
            password = await admin.post(
                "/api/dashboard-auth/guest/password", json={"password": "fixture-guest-password"}
            )
            assert password.status_code == 200
            login = await guest.post("/api/dashboard-auth/guest/login", json={"password": "fixture-guest-password"})
            assert login.status_code == 200

            payload = {
                "name": "Guest compatibility CPA",
                "baseUrl": await start(catalog),
                "apiKey": "fixture-cpa-key",
                "catalogMode": "cli_proxy_api",
                "supportsResponses": True,
            }
            created = await admin.post("/api/model-sources/", json=payload)
            assert created.status_code == 200
            source_id = created.json()["id"]
            listed = await guest.get("/api/model-sources/")
            assert listed.status_code == 200
            assert listed.json()["sources"][0]["id"] == source_id
            assert "fixture-cpa-key" not in listed.text

            denied = [
                await guest.post("/api/model-sources/", json=payload),
                await guest.patch(f"/api/model-sources/{source_id}", json={"isEnabled": False}),
                await guest.delete(f"/api/model-sources/{source_id}"),
            ]
            for response in denied:
                assert response.status_code == 403
                assert response.json()["error"]["code"] == "read_only_access"
            sources = (await admin.get("/api/model-sources/")).json()["sources"]
            assert len(sources) == 1
            assert sources[0]["isEnabled"] is True
            updated = await admin.patch(f"/api/model-sources/{source_id}", json={"name": "Updated CPA"})
            assert updated.status_code == 200

            # Dashboard cookies do not bypass the separate proxy authentication gate.
            assert (await guest.get("/v1/models")).status_code == 401
            discovered = await admin.get("/v1/models")
            assert discovered.status_code == 200
            ids = {model["id"] for model in discovered.json()["data"]}
            assert "guest-compatible-cpa" in ids
            assert {model["id"] for model in native} <= ids
            revoked = await admin.post("/api/dashboard-auth/guest/logout-all")
            assert revoked.status_code == 200
            stale_guest = await guest.get("/api/model-sources/")
            assert stale_guest.status_code == 401
            assert stale_guest.json()["error"]["code"] == "authentication_required"
            public_catalog = await admin.get("/v1/models")
            assert {model["id"] for model in public_catalog.json()["data"]} == ids
            assert (await admin.delete(f"/api/model-sources/{source_id}")).status_code == 204
