"""Bound admission, request bodies and same-origin access before route execution."""

import asyncio

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import CONCURRENCY


class Boundary:
    def __init__(self, app: ASGIApp, origin: str) -> None:
        self.app, self.origin, self.active = app, origin, 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend([
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'self'; frame-ancestors 'none'; "
                     b"form-action 'self'; object-src 'none'; base-uri 'none'"),
                ])
            await send(message)

        async def reject(status: int, error: str) -> None:
            await JSONResponse({"error": error}, status_code=status)(scope, receive, secure_send)

        headers = Headers(scope=scope)
        if headers.getlist("host") != [self.origin.removeprefix("http://")]:
            await reject(403, "Invalid host")
            return
        if scope["method"] not in ("GET", "HEAD"):
            if (headers.getlist("origin") != [self.origin]
                    or headers.get("content-type", "").split(";")[0] != "application/json"):
                await reject(403, "Invalid origin or content type")
                return
        if self.active >= CONCURRENCY:
            await reject(503, "Server busy; try again later")
            return
        self.active += 1
        try:
            # Buffer at most 4KiB before validation, including chunked bodies.
            body = bytearray()
            try:
                async with asyncio.timeout(10):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > 4096:
                            await reject(413, "Request too large")
                            return
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await reject(408, "Request body timed out")
                return
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            response_started = False

            async def track_send(message: Message) -> None:
                nonlocal response_started
                if message["type"] == "http.response.start":
                    response_started = True
                await secure_send(message)

            try:
                await self.app(scope, replay, track_send)
            except Exception:
                # Do not let driver/provider exception text reach responses or logs.
                if not response_started:
                    await reject(503, "Operation unavailable; outcome may be uncertain")
                else:
                    raise RuntimeError("Response interrupted; details suppressed") from None
        finally:
            self.active -= 1
