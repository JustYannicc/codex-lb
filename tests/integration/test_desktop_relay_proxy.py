from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer
from yarl import URL

from app.core.config.settings import get_settings
from app.modules.desktop_relay.api import _create_app

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def isolated_proxy_environment(monkeypatch):
    for name in os.environ:
        if name.lower() in {
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "socks_proxy",
            "ws_proxy",
            "wss_proxy",
            "no_proxy",
        }:
            monkeypatch.delenv(name)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("websocket", [False, True])
async def test_configured_http_proxy_carries_original_backend_identity(monkeypatch, websocket):
    calls = []

    async def proxy(request):
        calls.append(request.raw_path)
        assert request.headers["Authorization"] == "Bearer original"
        assert request.headers["chatgpt-account-id"] == "original-account"
        if websocket:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_str(await ws.receive_str())
            await ws.close()
            return ws
        assert await request.read() == b"original-body"
        return web.Response(body=b"proxy-response")

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", proxy)
    async with TestServer(app) as proxy_server:
        monkeypatch.setenv("HTTP_PROXY", str(proxy_server.make_url("")))
        monkeypatch.setenv("CODEX_LB_UPSTREAM_WEBSOCKET_TRUST_ENV", "true")
        get_settings.cache_clear()
        async with TestServer(_create_app(URL("http://127.0.0.1:1"), URL("http://backend.invalid"))) as relay:
            async with ClientSession() as client:
                headers = {
                    "Host": "localhost:8000",
                    "Authorization": "Bearer original",
                    "chatgpt-account-id": "original-account",
                }
                if websocket:
                    async with client.ws_connect(relay.make_url("/backend-api/ws"), headers=headers) as ws:
                        await ws.send_str("original-message")
                        assert await ws.receive_str() == "original-message"
                else:
                    async with client.post(
                        relay.make_url("/backend-api/settings?q=one"), headers=headers, data=b"original-body"
                    ) as response:
                        assert await response.read() == b"proxy-response"
    assert len(calls) == 1
    assert "backend.invalid/backend-api/" in calls[0]


async def test_local_lb_is_never_sent_through_outbound_proxy(monkeypatch):
    async def local(request):
        assert request.path == "/api/codex/desktop/usage"
        assert request.headers["Authorization"] == "Bearer original"
        return web.Response(text="local-usage")

    local_app = web.Application()
    local_app.router.add_route("*", "/{path:.*}", local)
    async with TestServer(local_app) as lb:
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
        get_settings.cache_clear()
        async with TestServer(_create_app(lb.make_url(""), URL("http://backend.invalid"))) as relay:
            async with ClientSession() as client:
                async with client.get(
                    relay.make_url("/backend-api/wham/usage"),
                    headers={"Host": "localhost:8000", "Authorization": "Bearer original"},
                ) as response:
                    assert response.status == 200
                    assert await response.text() == "local-usage"


async def test_websocket_explicit_direct_setting_overrides_proxy_environment(monkeypatch):
    async def upstream(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_str("direct")
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", upstream)
    async with TestServer(app) as upstream_server:
        monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("CODEX_LB_UPSTREAM_WEBSOCKET_TRUST_ENV", "false")
        get_settings.cache_clear()
        async with TestServer(_create_app(URL("http://127.0.0.1:1"), upstream_server.make_url(""))) as relay:
            async with ClientSession() as client:
                async with client.ws_connect(
                    relay.make_url("/backend-api/ws"), headers={"Host": "localhost:8000"}
                ) as ws:
                    assert await ws.receive_str() == "direct"


@asynccontextmanager
async def socks_proxy(upstream_port: int):
    tasks = set()
    destinations = []

    async def copy(reader, writer):
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()

    async def serve(reader, writer):
        peer = None
        pumps = []
        try:
            version, count = await reader.readexactly(2)
            assert version == 5
            await reader.readexactly(count)
            writer.write(b"\x05\x00")
            await writer.drain()
            assert await reader.readexactly(4) == b"\x05\x01\x00\x03"
            length = (await reader.readexactly(1))[0]
            host = (await reader.readexactly(length)).decode()
            port = int.from_bytes(await reader.readexactly(2))
            destinations.append((host, port))
            assert host == "backend.invalid" and port == upstream_port
            incoming, peer = await asyncio.open_connection("127.0.0.1", upstream_port)
            writer.write(b"\x05\x00\x00\x01\x7f\x00\x00\x01" + upstream_port.to_bytes(2))
            await writer.drain()
            pumps = [asyncio.create_task(copy(reader, peer)), asyncio.create_task(copy(incoming, writer))]
            await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in pumps:
                task.cancel()
            await asyncio.gather(*pumps, return_exceptions=True)
            if peer is not None:
                peer.close()
                await peer.wait_closed()
            writer.close()
            await writer.wait_closed()

    def accept(reader, writer):
        task = asyncio.create_task(serve(reader, writer))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    server = await asyncio.start_server(accept, "127.0.0.1", 0)
    try:
        yield f"socks5h://127.0.0.1:{server.sockets[0].getsockname()[1]}", destinations
    finally:
        server.close()
        await server.wait_closed()
        pending = list(tasks)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


@pytest.mark.parametrize("websocket", [False, True])
async def test_socks_proxy_tunnels_http_and_websocket_with_remote_dns(monkeypatch, websocket):
    async def upstream(request):
        assert request.headers["Authorization"] == "Bearer original"
        if websocket:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_str("tunneled")
            await ws.close()
            return ws
        return web.Response(text="tunneled")

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", upstream)
    async with TestServer(app) as upstream_server:
        port = upstream_server.port
        assert isinstance(port, int)
        async with socks_proxy(port) as (proxy, destinations):
            monkeypatch.setenv("SOCKS_PROXY", proxy)
            monkeypatch.setenv("CODEX_LB_UPSTREAM_WEBSOCKET_TRUST_ENV", "true")
            get_settings.cache_clear()
            origin = URL(f"http://backend.invalid:{upstream_server.port}")
            async with TestServer(_create_app(URL("http://127.0.0.1:1"), origin)) as relay:
                async with ClientSession() as client:
                    headers = {"Host": "localhost:8000", "Authorization": "Bearer original"}
                    if websocket:
                        async with client.ws_connect(relay.make_url("/backend-api/ws"), headers=headers) as ws:
                            assert await ws.receive_str() == "tunneled"
                    else:
                        async with client.get(relay.make_url("/backend-api/settings"), headers=headers) as response:
                            assert await response.text() == "tunneled"
            assert destinations == [("backend.invalid", upstream_server.port)]
