"""ASGI middleware: request ids, security headers, body-size limits and rate limiting."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var


class SlidingWindowLimiter:
    """In-process limiter (single API instance). Swap for Redis when running multiple API replicas."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cross-origin-opener-policy", b"same-origin"),
]


async def _send_json(send: Send, status: int, code: str, message: str) -> None:
    body = ('{"error":{"code":"%s","message":"%s","details":{}}}' % (code, message)).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})  # fmt: skip
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, *, max_body: int, per_minute: int, auth_per_minute: int, hsts: bool) -> None:
        self.app, self.max_body, self.per_minute, self.hsts = app, max_body, per_minute, hsts
        self.auth_per_minute = auth_per_minute

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        rid = headers.get(b"x-request-id", b"").decode()[:64] or uuid.uuid4().hex
        token = request_id_var.set(rid)
        client = scope.get("client") or ("unknown", 0)
        path: str = scope.get("path", "")
        try:
            if path.startswith("/api/") and not path.endswith("/content"):
                if not limiter.allow(f"ip:{client[0]}", self.per_minute):
                    await _send_json(send, 429, "rate_limited", "Too many requests, slow down.")
                    return
                if path.startswith("/api/v1/auth/") and scope.get("method") == "POST":
                    if not limiter.allow(f"auth:{client[0]}", self.auth_per_minute):
                        await _send_json(send, 429, "rate_limited", "Too many authentication attempts.")
                        return
            length = headers.get(b"content-length")
            if length and length.isdigit() and int(length) > self.max_body:
                await _send_json(send, 413, "payload_too_large", "Request body too large.")
                return

            received = 0

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > self.max_body:
                        raise _TooLarge()
                return message

            async def secure_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    extra = list(_SECURITY_HEADERS) + [(b"x-request-id", rid.encode())]
                    if path.startswith("/api/") and not path.endswith("/content"):
                        extra.append((b"cache-control", b"no-store"))
                    if self.hsts:
                        extra.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains"))
                    message["headers"] = list(message.get("headers", [])) + extra
                await send(message)

            try:
                await self.app(scope, limited_receive, secure_send)
            except _TooLarge:
                await _send_json(send, 413, "payload_too_large", "Request body too large.")
        finally:
            request_id_var.reset(token)


class _TooLarge(Exception):
    pass
