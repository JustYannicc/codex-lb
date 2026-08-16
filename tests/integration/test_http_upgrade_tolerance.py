"""Regression tests for issue #1757: h2c upgrade offers must not break requests.

JetBrains/Ktor clients opportunistically attach ``Connection: Upgrade`` +
``Upgrade: h2c`` + ``HTTP2-Settings`` to plain HTTP/1.1 POSTs. The stock
uvicorn httptools protocol treats any such request as a protocol switch and
wedges the parser: a body coalesced with the headers is silently dropped, and
a body written as a separate segment (Ktor's pattern) turns into
``400 Invalid HTTP request received.``.

The suite covers three layers:

- protocol-level tests driving ``UpgradeTolerantHttpToolsProtocol`` through a
  fake transport with both client segmentations;
- canary tests pinning the stock behavior these fixes exist for (if a uvicorn
  upgrade makes them fail, the subclass can likely be retired);
- a live-server test using the production protocol wiring over real sockets,
  including a real WebSocket upgrade that must keep completing.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
import uvicorn
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol
from uvicorn.server import ServerState

from app.cli import _load_http_protocol_class
from app.core.http_protocol import UpgradeTolerantHttpToolsProtocol

pytestmark = pytest.mark.integration

_BODY = json.dumps({"model": "gpt-5.6-luna", "input": "hello", "stream": False}).encode()
_H2C_HEAD = (
    b"POST /echo HTTP/1.1\r\n"
    b"Host: 127.0.0.1\r\n"
    b"Connection: Upgrade, HTTP2-Settings\r\n"
    b"Upgrade: h2c\r\n"
    b"HTTP2-Settings: AAMAAABkAARAAAAAAAIAAAAA\r\n"
    b"Content-Type: application/json\r\n"
    b"Content-Length: " + str(len(_BODY)).encode() + b"\r\n"
    b"\r\n"
)


async def _echo_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    """Echo the request body and the header names the application observed."""
    if scope["type"] == "websocket":
        await receive()
        await send({"type": "websocket.accept"})
        message = await receive()
        await send({"type": "websocket.send", "text": message.get("text", "")})
        await send({"type": "websocket.close"})
        return

    assert scope["type"] == "http"
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    payload = json.dumps(
        {
            "echo": body.decode(),
            "header_names": sorted({name.decode() for name, _ in scope["headers"]}),
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": payload})


class _FakeTransport(asyncio.Transport):
    def __init__(self) -> None:
        super().__init__()
        self.buffer = bytearray()
        self.closed = False
        self.protocol: asyncio.BaseProtocol | None = None

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    def is_closing(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True

    def abort(self) -> None:
        self.closed = True

    def pause_reading(self) -> None:
        pass

    def resume_reading(self) -> None:
        pass

    def set_protocol(self, protocol: asyncio.BaseProtocol) -> None:
        self.protocol = protocol

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        if name == "sockname":
            return ("127.0.0.1", 2455)
        if name == "peername":
            return ("127.0.0.1", 54321)
        return default


def _make_protocol(protocol_class: type[HttpToolsProtocol]) -> tuple[HttpToolsProtocol, _FakeTransport]:
    config = uvicorn.Config(app=_echo_app, lifespan="off")
    config.load()
    protocol = protocol_class(config=config, server_state=ServerState(), app_state={})
    transport = _FakeTransport()
    protocol.connection_made(transport)
    return protocol, transport


async def _wait_for_response(transport: _FakeTransport, timeout: float = 5.0) -> bytes:
    async with asyncio.timeout(timeout):
        while b"\r\n\r\n" not in transport.buffer or not bytes(transport.buffer).split(b"\r\n\r\n", 1)[1]:
            await asyncio.sleep(0.01)
    return bytes(transport.buffer)


def _parse_json_body(raw_response: bytes) -> dict[str, Any]:
    _, _, body = raw_response.partition(b"\r\n\r\n")
    return json.loads(body)


async def test_h2c_offer_with_coalesced_body_is_served_as_http11() -> None:
    protocol, transport = _make_protocol(UpgradeTolerantHttpToolsProtocol)

    protocol.data_received(_H2C_HEAD + _BODY)

    raw_response = await _wait_for_response(transport)
    assert raw_response.startswith(b"HTTP/1.1 200 OK"), raw_response
    payload = _parse_json_body(raw_response)
    assert payload["echo"] == _BODY.decode()
    # The declined offer's hop-by-hop headers must not reach the application.
    assert "upgrade" not in payload["header_names"]
    assert "http2-settings" not in payload["header_names"]
    assert "connection" not in payload["header_names"]
    assert not transport.closed


async def test_h2c_offer_with_split_head_and_body_is_served_as_http11() -> None:
    protocol, transport = _make_protocol(UpgradeTolerantHttpToolsProtocol)

    protocol.data_received(_H2C_HEAD)
    await asyncio.sleep(0.01)
    protocol.data_received(_BODY)

    raw_response = await _wait_for_response(transport)
    assert raw_response.startswith(b"HTTP/1.1 200 OK"), raw_response
    assert _parse_json_body(raw_response)["echo"] == _BODY.decode()
    assert not transport.closed


async def test_h2c_offer_keeps_connection_reusable_for_next_request() -> None:
    protocol, transport = _make_protocol(UpgradeTolerantHttpToolsProtocol)

    protocol.data_received(_H2C_HEAD + _BODY)
    await _wait_for_response(transport)
    transport.buffer.clear()

    follow_up = b"POST /echo HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\n\r\nhi"
    protocol.data_received(follow_up)

    raw_response = await _wait_for_response(transport)
    assert raw_response.startswith(b"HTTP/1.1 200 OK"), raw_response
    assert _parse_json_body(raw_response)["echo"] == "hi"


async def test_stock_httptools_protocol_still_breaks_on_h2c_offers() -> None:
    """Canary pinning the upstream defect this module works around.

    The stock parser drops a coalesced body (the application observes an empty
    body) and answers 400 when the body arrives as a separate segment. If a
    uvicorn/httptools upgrade makes this test fail, upstream has fixed
    https://github.com/Soju06/codex-lb/issues/1757 and
    ``UpgradeTolerantHttpToolsProtocol`` can likely be retired.
    """
    protocol, transport = _make_protocol(HttpToolsProtocol)
    protocol.data_received(_H2C_HEAD + _BODY)
    raw_response = await _wait_for_response(transport)
    assert raw_response.startswith(b"HTTP/1.1 200 OK")
    assert _parse_json_body(raw_response)["echo"] == ""  # body silently dropped

    protocol, transport = _make_protocol(HttpToolsProtocol)
    protocol.data_received(_H2C_HEAD)
    await asyncio.sleep(0.01)
    protocol.data_received(_BODY)
    async with asyncio.timeout(5.0):
        while b"Invalid HTTP request received." not in transport.buffer:
            await asyncio.sleep(0.01)
    # The body segment hits the wedged parser: the application never sees the
    # payload and the client's request ends in a 400.
    assert b'"echo": ""' in transport.buffer
    assert b"HTTP/1.1 400 Bad Request" in transport.buffer


async def test_live_server_serves_h2c_offers_and_websocket_upgrades() -> None:
    """End-to-end proof over real sockets with the production protocol wiring."""
    config = uvicorn.Config(
        app=_echo_app,
        host="127.0.0.1",
        port=0,
        http=_load_http_protocol_class(),
        lifespan="off",
        log_level="warning",
    )
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(10.0):
            while not server.started:
                await asyncio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]

        # Ktor's write pattern: headers first, body as a separate segment.
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(_H2C_HEAD)
        await writer.drain()
        await asyncio.sleep(0.05)
        writer.write(_BODY)
        await writer.drain()
        async with asyncio.timeout(10.0):
            status_line = await reader.readline()
            assert status_line == b"HTTP/1.1 200 OK\r\n"
            raw_headers = await reader.readuntil(b"\r\n\r\n")
            content_length = next(
                int(line.split(b":", 1)[1])
                for line in raw_headers.lower().splitlines()
                if line.startswith(b"content-length:")
            )
            payload = json.loads(await reader.readexactly(content_length))
        assert payload["echo"] == _BODY.decode()
        writer.close()
        await writer.wait_closed()

        # A real WebSocket upgrade must keep switching protocols.
        from websockets.asyncio.client import connect

        async with connect(f"ws://127.0.0.1:{port}/ws") as websocket:
            await websocket.send("ping")
            assert await websocket.recv() == "ping"
    finally:
        server.should_exit = True
        async with asyncio.timeout(10.0):
            await serve_task
