"""Reject large requests before the framework reads them into memory.

Only a declared Content-Length is accepted. Chunked requests without a
length are refused. Uvicorn does not read past the declared length.
This middleware sits outside the access logger, so it writes its own line.
"""

import json
import logging

from chatbot_agent.core.security import MAX_BODY_BYTES, safe_log_value

logger = logging.getLogger("chatbot_agent.access")


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        lengths = [
            value for key, value in scope.get("headers", []) if key.lower() == b"content-length"
        ]
        if len(lengths) != 1:
            await _reject(scope, send, 411, "length_required", "Content-Length is required.")
            return
        raw = lengths[0]
        if not raw.isdigit() or len(raw) > 6:
            await _reject(scope, send, 400, "invalid_length", "Content-Length is invalid.")
            return
        if int(raw) > self.max_bytes:
            await _reject(scope, send, 413, "payload_too_large", "Request body is too large.")
            return
        await self.app(scope, receive, send)


async def _reject(scope, send, status: int, code: str, message: str) -> None:
    request_id = scope.get("state", {}).get("request_id", "-")
    logger.info(
        "request_id=%s user=- method=%s path=%s status=%s",
        safe_log_value(request_id),
        safe_log_value(scope.get("method", "")),
        safe_log_value(scope.get("path", "")),
        status,
    )
    await _send_error(send, status, code, message)


async def _send_error(send, status: int, code: str, message: str) -> None:
    body = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"x-content-type-options", b"nosniff"),
        (b"cache-control", b"no-store"),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
