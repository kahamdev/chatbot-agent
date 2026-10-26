"""Per-request auth, rate limit, and service lookup."""

from fastapi import Request

from chatbot_agent.core.config import Settings
from chatbot_agent.core.security import User, authenticate
from chatbot_agent.services.chat_service import ChatService


def current_settings(request: Request) -> Settings:
    return request.app.state.settings


def current_user(request: Request) -> User:
    settings: Settings = request.app.state.settings
    authorization = request.headers.get("authorization")
    user = authenticate(settings.auth_enabled, settings.parsed_api_keys, authorization)
    request.app.state.rate_limiter.check(user.user_id)
    request.state.user_id = user.user_id
    return user


def current_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
