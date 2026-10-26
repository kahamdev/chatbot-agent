"""FastAPI application factory.

Tracing flags are set before LangChain is imported. The route handlers stay
thin: auth and limits are dependencies, and the graph lives in the service.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from chatbot_agent import __version__
from chatbot_agent.core.config import Settings, get_settings
from chatbot_agent.core.exceptions import AppError
from chatbot_agent.core.logging import configure_logging
from chatbot_agent.core.security import MAX_BODY_BYTES, RateLimiter
from chatbot_agent.core.tracing import configure_tracing
from chatbot_agent.middleware.body_limit import BodyLimitMiddleware
from chatbot_agent.middleware.logging import AccessLogMiddleware
from chatbot_agent.middleware.request_id import RequestIdMiddleware, request_id_from
from chatbot_agent.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    active = settings or get_settings()
    configure_logging(active.log_level)
    configure_tracing(active)

    # Imported after tracing flags are set.
    from chatbot_agent.api.routes.chat import router as chat_router
    from chatbot_agent.api.routes.health import router as health_router
    from chatbot_agent.services.chat_service import build_chat_service

    docs = None if active.app_env == "production" else "/docs"
    app = FastAPI(
        title=active.app_name,
        version=__version__,
        docs_url=docs,
        redoc_url=None if docs is None else "/redoc",
        openapi_url=None if docs is None else "/openapi.json",
    )
    app.state.settings = active
    app.state.rate_limiter = RateLimiter(active.rate_limit_per_minute)
    app.state.chat_service = build_chat_service(active)

    _add_middleware(app, active)
    _add_error_handlers(app)
    app.include_router(health_router)
    app.include_router(chat_router, prefix=active.api_prefix)
    logger.info(
        "Starting %s env=%s auth=%s model=%s",
        active.app_name,
        active.app_env,
        active.auth_enabled,
        active.model_provider,
    )
    return app


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    # The last middleware added is the first to see the request.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AccessLogMiddleware)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            max_age=600,
        )
    app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    app.add_middleware(RequestIdMiddleware)
    if settings.trusted_host_list:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)


def _add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Request rejected code=%s status=%s request_id=%s",
            exc.code,
            exc.status_code,
            request_id_from(request),
        )
        return _error(request, exc.code, exc.message, exc.status_code, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Invalid request request_id=%s", request_id_from(request))
        return _error(request, "invalid_request", "The request is invalid.", 422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        messages = {404: "Not found.", 405: "Method not allowed.", 400: "Bad request."}
        message = messages.get(exc.status_code, "Request could not be processed.")
        return _error(request, "http_error", message, exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error request_id=%s error_type=%s",
            request_id_from(request),
            type(exc).__name__,
        )
        return _error(request, "internal_error", "Something went wrong.", 500)


def _error(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id_from(request),
            }
        },
    )


app = create_app()


if __name__ == "__main__":
    import uvicorn

    runtime = get_settings()
    uvicorn.run(
        "chatbot_agent.main:app",
        host=runtime.host,
        port=runtime.port,
        proxy_headers=False,
        server_header=False,
    )
