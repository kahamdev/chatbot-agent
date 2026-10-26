import asyncio
import json

from chatbot_agent.middleware.body_limit import BodyLimitMiddleware


def _run(headers: list[tuple[bytes, bytes]]) -> tuple[int, dict]:
    captured: dict[str, object] = {}

    async def app(scope, receive, send) -> None:
        captured["called"] = True

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    sent: list[dict] = []

    async def send(message) -> None:
        sent.append(message)

    middleware = BodyLimitMiddleware(app, max_bytes=64)
    scope = {"type": "http", "method": "POST", "headers": headers}
    asyncio.run(middleware(scope, receive, send))
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = next(message["body"] for message in sent if message["type"] == "http.response.body")
    captured["status"] = status
    return status, json.loads(body)


def test_rejects_missing_and_large_lengths() -> None:
    status, body = _run([])
    assert status == 411
    assert body["error"]["code"] == "length_required"

    status, body = _run([(b"content-length", b"65")])
    assert status == 413
    assert body["error"]["code"] == "payload_too_large"


def test_allows_a_small_declared_length() -> None:
    called = False

    async def app(scope, receive, send) -> None:
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message) -> None:
        return None

    middleware = BodyLimitMiddleware(app, max_bytes=64)
    scope = {"type": "http", "method": "POST", "headers": [(b"content-length", b"2")]}
    asyncio.run(middleware(scope, receive, send))
    assert called
