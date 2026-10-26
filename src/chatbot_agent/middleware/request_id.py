"""Attach a request id without reading the body.

Pure ASGI avoids buffering the payload before the body-size check runs.
"""

import re
import uuid

from starlette.requests import Request

_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class RequestIdMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, b"x-request-id")
        request_id = incoming if _REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_id)


def request_id_from(request: Request) -> str:
    return str(getattr(request.state, "request_id", None) or "unknown")


def _header(scope, name: bytes) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("ascii", errors="ignore")
    return ""
