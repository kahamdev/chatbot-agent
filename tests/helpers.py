"""A chat model that returns scripted replies, for graph tests."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


class ScriptedModel(BaseChatModel):
    _replies: list[AIMessage] = PrivateAttr(default_factory=list)

    def __init__(self, replies: list[AIMessage]) -> None:
        super().__init__()
        self._replies = list(replies)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self._replies:
            message = self._replies.pop(0)
        else:
            message = AIMessage(content="No scripted reply left.")
        return ChatResult(generations=[ChatGeneration(message=message)])
