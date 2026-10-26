"""One access line per request. The body, query string, and headers are omitted."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from chatbot_agent.core.security import safe_log_value

logger = logging.getLogger("chatbot_agent.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            user_id = getattr(request.state, "user_id", "-")
            request_id = getattr(request.state, "request_id", "-")
            logger.info(
                "request_id=%s user=%s method=%s path=%s status=%s latency_ms=%.1f",
                safe_log_value(request_id),
                safe_log_value(user_id),
                safe_log_value(request.method),
                safe_log_value(request.url.path),
                status,
                elapsed_ms,
            )
