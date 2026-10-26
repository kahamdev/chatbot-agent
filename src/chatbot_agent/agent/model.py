"""Model construction.

``local`` is a deterministic stand-in so the API and graph run without a
provider key. It follows a few visible rules. It is not a safety filter for
a hosted model. The hosted model uses the same graph, tool allowlist, and
step limits.
"""

import re
import uuid

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from chatbot_agent.agent.policies import message_text
from chatbot_agent.core.config import Settings
from chatbot_agent.tools.knowledge_search import has_knowledge_match

_ALLOWED_EXPRESSION_CHARS = set("0123456789.+-*/() ")
_GREETINGS = {"hello", "hi", "hey"}
_HELP = "I can help with arithmetic and with questions about this chatbot's tools and limits."


class LocalChatModel(BaseChatModel):
    """Rule-based chat model used when MODEL_PROVIDER=local."""

    model_name: str = "local"

    @property
    def _llm_type(self) -> str:
        return "local-chat"

    def bind_tools(self, tools, **kwargs):
        """Tool choice is decided in ``_reply``. Schemas are not required."""
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: object = None,
        **kwargs: object,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        if not messages:
            return AIMessage(content=_HELP)
        last = messages[-1]
        if isinstance(last, ToolMessage):
            return _quote_tool_result(last)

        text = message_text(last).strip()
        expression = extract_expression(text)
        if expression is not None:
            return _tool_call("calculator", {"expression": expression})
        if has_knowledge_match(text):
            return _tool_call("knowledge_search", {"query": text[:200]})
        if _normalized(text) in _GREETINGS:
            return AIMessage(content=f"Hello. {_HELP}")
        return AIMessage(content=_HELP)


def extract_expression(text: str) -> str | None:
    """Pull one arithmetic span out of a sentence, ignoring the other words."""
    cleaned = "".join(char if char in _ALLOWED_EXPRESSION_CHARS else " " for char in text[:2000])
    candidates = [cleaned.strip()]
    candidates.extend(part.strip() for part in cleaned.split("  ") if part.strip())
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        compact = candidate.replace(" ", "")
        if not 3 <= len(compact) <= 100:
            continue
        if not any(operator in compact for operator in "+-*/"):
            continue
        if not any(char.isdigit() for char in compact):
            continue
        if re.fullmatch(r"[0-9+\-*/().]+", compact):
            return " ".join(candidate.split())
    return None


def build_model(settings: Settings) -> BaseChatModel:
    if settings.model_provider == "local":
        return LocalChatModel()
    key = settings.model_api_key.get_secret_value().strip()
    if not key:
        raise RuntimeError("MODEL_API_KEY is required for the openai provider.")
    try:
        from langchain.chat_models import init_chat_model
    except ImportError:
        raise RuntimeError("The openai provider is not installed.") from None
    try:
        model = init_chat_model(
            settings.model_name,
            model_provider="openai",
            temperature=settings.model_temperature,
            timeout=settings.model_timeout_seconds,
            max_tokens=settings.max_output_tokens,
            api_key=key,
        )
    except Exception:
        raise RuntimeError(
            "Could not create the OpenAI model. Check MODEL_NAME and MODEL_API_KEY."
        ) from None
    if not isinstance(model, BaseChatModel):
        raise RuntimeError("The configured model is not a chat model.")
    return model


def _tool_call(name: str, args: dict) -> AIMessage:
    call_id = f"call_{name}_{uuid.uuid4().hex[:12]}"
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def _quote_tool_result(message: ToolMessage) -> AIMessage:
    """Show tool output as data. Do not treat it as a new instruction."""
    body = message_text(message).strip()[:1000]
    if message.name == "calculator":
        return AIMessage(content=f"The result is {body}.")
    return AIMessage(content=f"From the knowledge base: {body}")


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z\s]", "", text.lower()).strip()
