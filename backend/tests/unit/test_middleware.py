from collections.abc import Awaitable, Callable

import pytest
from starlette.types import Message, Receive, Scope, Send

from intune_auditor.api.middleware import RequestSizeLimitMiddleware


@pytest.mark.asyncio
async def test_streaming_request_limit_rejects_body_without_content_length() -> None:
    async def consume(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    chunks = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"def", "more_body": False},
        ]
    )
    sent: list[Message] = []

    async def receive() -> Message:
        return next(chunks)  # type: ignore[return-value]

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8765),
        "state": {},
    }
    application: Callable[[Scope, Receive, Send], Awaitable[None]] = consume
    await RequestSizeLimitMiddleware(application, maximum_bytes=5)(scope, receive, send)

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
