"""Request correlation, error envelopes, and browser security headers."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from intune_auditor.api.errors import ProblemError

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    """Bound request bodies even when a client omits Content-Length."""

    def __init__(self, app: ASGIApp, maximum_bytes: int) -> None:
        self.app = app
        self.maximum_bytes = maximum_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(scope.setdefault("state", {}).get("request_id", str(uuid4())))[:128]
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = self.maximum_bytes + 1
        if content_length > self.maximum_bytes:
            await self._reject(scope, receive, send, request_id)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.maximum_bytes:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            await self._reject(scope, receive, send, request_id)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, request_id: str) -> None:
        path = str(scope.get("path", "/"))
        response = JSONResponse(
            {
                "type": "about:blank",
                "title": "Request too large",
                "status": 413,
                "detail": "The request exceeds the configured upload limit.",
                "instance": path,
                "request_id": request_id,
            },
            status_code=413,
            media_type="application/problem+json",
        )
        await response(scope, receive, send)


class _RequestBodyTooLarge(Exception):
    pass


class SecurityAndRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
        request.state.request_id = request_id
        response: Response
        try:
            response = await call_next(request)
        except ProblemError as exc:
            body: dict[str, Any] = {
                "type": exc.error_type,
                "title": exc.title,
                "status": exc.status,
                "detail": exc.detail,
                "instance": str(request.url.path),
                "request_id": request_id,
                **exc.extensions,
            }
            response = JSONResponse(
                body, status_code=exc.status, media_type="application/problem+json"
            )
        except Exception:
            logger.exception("Unhandled request failure", extra={"request_id": request_id})
            response = JSONResponse(
                {
                    "type": "about:blank",
                    "title": "Internal server error",
                    "status": 500,
                    "detail": "The request could not be completed.",
                    "instance": str(request.url.path),
                    "request_id": request_id,
                },
                status_code=500,
                media_type="application/problem+json",
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response
