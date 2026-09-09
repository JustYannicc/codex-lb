from __future__ import annotations

import asyncio
import ipaddress
import logging
from collections.abc import AsyncIterator

from aiohttp import (
    ClientError,
    ClientRequest,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    DummyCookieJar,
    WSMsgType,
    web,
)
from aiohttp.client_middlewares import ClientHandlerType
from multidict import CIMultiDict
from yarl import URL

_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}
_WS_HEADERS = {"sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions", "sec-websocket-protocol"}


def validate_lb_url(value: str) -> URL:
    message = "--lb-url must be an HTTP(S) loopback origin without credentials, path, query or fragment"
    try:
        url = URL(value)
        host = url.host
        loopback = host == "localhost" or (host is not None and ipaddress.ip_address(host).is_loopback)
        valid = url.scheme in {"http", "https"} and loopback and url.port is not None
    except ValueError:
        raise ValueError(message) from None
    if not valid or url.user is not None or url.query_string or url.fragment or url.path != "/":
        raise ValueError(message)
    return url


def _headers(raw: tuple[tuple[bytes, bytes], ...], *, websocket: bool = False) -> CIMultiDict[str]:
    headers = CIMultiDict(
        (key.decode("utf-8", "surrogateescape"), value.decode("utf-8", "surrogateescape")) for key, value in raw
    )
    excluded = _HOP_HEADERS | {
        token.strip().lower() for value in headers.getall("Connection", []) for token in value.split(",")
    }
    if websocket:
        excluded |= _WS_HEADERS
    return CIMultiDict((key, value) for key, value in headers.items() if key.lower() not in excluded)


class _HandshakeResponse(Exception):
    def __init__(self, response: ClientResponse) -> None:
        self.response = response
        super().__init__("Upstream did not accept the WebSocket handshake")


async def _preserve_websocket_failure(request: ClientRequest, handler: ClientHandlerType) -> ClientResponse:
    response = await handler(request)
    if request.headers.get("Upgrade", "").lower() == "websocket" and response.status != 101:
        # Return the original failure through the relay before aiohttp follows
        # a redirect or discards the handshake response body. The caller owns it.
        raise _HandshakeResponse(response)
    return response


async def _pump(
    source: ClientWebSocketResponse | web.WebSocketResponse,
    target: ClientWebSocketResponse | web.WebSocketResponse,
) -> None:
    while True:
        message = await source.receive()
        if message.type == WSMsgType.TEXT:
            await target.send_str(message.data)
        elif message.type == WSMsgType.BINARY:
            await target.send_bytes(message.data)
        elif message.type == WSMsgType.PING:
            await target.ping(message.data)
        elif message.type == WSMsgType.PONG:
            await target.pong(message.data)
        elif message.type == WSMsgType.CLOSE:
            await target.close(code=message.data, message=(message.extra or "").encode("utf-8"))
            return
        elif message.type in {WSMsgType.ERROR, WSMsgType.CLOSED, WSMsgType.CLOSING}:
            await target.close(code=source.close_code or 1011)
            return


async def _websocket(request: web.Request, session: ClientSession, target: URL) -> web.WebSocketResponse:
    protocols = tuple(
        item.strip() for item in request.headers.get("Sec-WebSocket-Protocol", "").split(",") if item.strip()
    )
    async with session.ws_connect(
        target,
        headers=_headers(request.raw_headers, websocket=True),
        protocols=protocols,
        autoping=False,
        autoclose=False,
        max_msg_size=16 * 1024 * 1024,
    ) as upstream:
        downstream = web.WebSocketResponse(
            protocols=(upstream.protocol,) if upstream.protocol else (),
            autoping=False,
            autoclose=False,
            max_msg_size=16 * 1024 * 1024,
        )
        # aiohttp owns the handshake fields; retain other end-to-end metadata.
        for key, value in _headers(upstream._response.raw_headers, websocket=True).items():
            if key.lower() != "sec-websocket-accept":
                downstream.headers.add(key, value)
        await downstream.prepare(request)
        tasks = [asyncio.create_task(_pump(upstream, downstream)), asyncio.create_task(_pump(downstream, upstream))]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await downstream.close()
        return downstream


def create_app(lb_url: str = "http://127.0.0.1:2455") -> web.Application:
    return _create_app(validate_lb_url(lb_url), URL("https://chatgpt.com"))


def _create_app(lb_origin: URL, backend_origin: URL, *, timeout: float = 60) -> web.Application:
    # Destination injection is private and used only by isolated transport tests.
    app = web.Application(handler_args={"auto_decompress": False})
    session_key = web.AppKey("relay_session", ClientSession)

    async def lifespan(application: web.Application) -> AsyncIterator[None]:
        async with ClientSession(
            cookie_jar=DummyCookieJar(),
            middlewares=[_preserve_websocket_failure],
            auto_decompress=False,
            trust_env=False,
            timeout=ClientTimeout(total=None, connect=10, sock_read=timeout),
            skip_auto_headers={"User-Agent", "Accept-Encoding", "Content-Type"},
        ) as session:
            # aiohttp retries idempotent requests on a dropped reused connection by default.
            session._retry_connection = False
            application[session_key] = session
            yield

    async def relay(request: web.Request) -> web.StreamResponse:
        if request.headers.getall("Host", []) != ["localhost:8000"]:
            raise web.HTTPForbidden(text="Unexpected relay authority")
        if not request.raw_path.startswith("/backend-api/") or not request.path.startswith("/backend-api/"):
            raise web.HTTPNotFound()
        usage = request.method == "GET" and request.path in {"/backend-api/wham/usage", "/backend-api/wham/usage/"}
        raw_path = request.raw_path
        if usage:
            raw_path = "/api/codex/desktop/usage" + (
                "?" + request.rel_url.raw_query_string if request.rel_url.raw_query_string else ""
            )
        target = URL(str(lb_origin if usage else backend_origin).rstrip("/") + raw_path, encoded=True)
        session = request.app[session_key]
        response: web.StreamResponse | None = None
        try:
            if request.headers.get("Upgrade", "").lower() == "websocket":
                if usage:
                    raise web.HTTPBadRequest(text="Usage does not support WebSocket")
                try:
                    return await _websocket(request, session, target)
                except _HandshakeResponse as failure:
                    pending_response = failure.response
            else:
                pending_response = session.request(
                    request.method,
                    target,
                    headers=_headers(request.raw_headers),
                    data=request.content.iter_chunked(65536) if request.can_read_body else None,
                    allow_redirects=False,
                )
            async with pending_response as upstream:
                response = web.StreamResponse(status=upstream.status, headers=_headers(upstream.raw_headers))
                await response.prepare(request)
                async for chunk in upstream.content.iter_chunked(65536):
                    await response.write(chunk)
                await response.write_eof()
                return response
        except (ClientError, TimeoutError, ConnectionError):
            if response is not None and response.prepared:
                if request.transport is not None:
                    request.transport.close()
                return response
            return web.Response(status=502, text="Desktop relay upstream unavailable")

    app.cleanup_ctx.append(lifespan)
    app.router.add_route("*", "/{path:.*}", relay)
    return app


def run(lb_url: str) -> None:
    app = create_app(lb_url)
    # Error records can contain URL or parser input. This listener deliberately emits none.
    silent_logger = logging.Logger("codex_lb.desktop_relay", level=logging.CRITICAL + 1)
    web.run_app(
        app,
        host=["127.0.0.1", "::1"],
        port=8000,
        access_log=None,
        handler_cancellation=True,
        logger=silent_logger,
        print=None,
    )
