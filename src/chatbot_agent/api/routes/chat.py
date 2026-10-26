"""Chat endpoint. The handler checks the request, then calls the service."""

import asyncio

from fastapi import APIRouter, Depends, Request

from chatbot_agent.api.dependencies import current_chat_service, current_settings, current_user
from chatbot_agent.api.schemas import ChatRequest, ChatResponse, ErrorResponse
from chatbot_agent.core.config import Settings
from chatbot_agent.core.exceptions import AppError
from chatbot_agent.core.security import User
from chatbot_agent.middleware.request_id import request_id_from
from chatbot_agent.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat(
    body: ChatRequest,
    request: Request,
    settings: Settings = Depends(current_settings),
    user: User = Depends(current_user),
    service: ChatService = Depends(current_chat_service),
) -> ChatResponse:
    if len(body.message) > settings.max_request_chars:
        raise AppError("payload_too_large", "Message is too long.", 413)
    try:
        answer = await asyncio.wait_for(
            asyncio.to_thread(
                service.reply,
                user.user_id,
                body.message,
                body.thread_id,
                request_id_from(request),
            ),
            timeout=settings.model_timeout_seconds,
        )
    except TimeoutError:
        raise AppError("timeout", "The request took too long.", 504) from None
    return ChatResponse(
        thread_id=answer.thread_id,
        message=answer.message,
        request_id=request_id_from(request),
    )
