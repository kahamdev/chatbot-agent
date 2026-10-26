"""Process health. These routes do not require a client credential."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready(request: Request) -> dict[str, str] | JSONResponse:
    if getattr(request.app.state, "chat_service", None) is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
