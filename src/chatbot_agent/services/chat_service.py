"""Run one user turn through the graph and return the final answer."""

import logging
from dataclasses import dataclass

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from chatbot_agent.agent.graph import build_graph
from chatbot_agent.agent.policies import cap_text, final_ai_text
from chatbot_agent.core.config import Settings
from chatbot_agent.core.exceptions import AppError
from chatbot_agent.core.tracing import invoke_with_optional_trace
from chatbot_agent.storage.checkpointer import build_checkpointer
from chatbot_agent.storage.threads import ThreadRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatAnswer:
    thread_id: str
    message: str


class ChatService:
    def __init__(self, settings: Settings, graph, threads: ThreadRegistry) -> None:
        self._settings = settings
        self._graph = graph
        self._threads = threads

    @property
    def graph(self):
        return self._graph

    def reply(
        self,
        user_id: str,
        message: str,
        thread_id: str | None,
        request_id: str,
    ) -> ChatAnswer:
        public_id = self._threads.resolve(user_id, thread_id)
        config = {
            "configurable": {"thread_id": f"{user_id}:{public_id}"},
            "recursion_limit": self._settings.max_graph_steps,
        }
        payload = {
            "messages": [HumanMessage(content=message)],
            "tool_calls_used": 0,
            "blocked": False,
        }
        try:
            state = invoke_with_optional_trace(self._graph, payload, config, self._settings)
        except GraphRecursionError:
            logger.warning("Graph step limit reached request_id=%s", request_id)
            return ChatAnswer(
                thread_id=public_id,
                message="I stopped because this request needed too many steps.",
            )
        except AppError:
            raise
        except Exception as exc:
            logger.error(
                "Chat graph failed request_id=%s error_type=%s",
                request_id,
                type(exc).__name__,
            )
            raise AppError(
                "assistant_unavailable",
                "The assistant is unavailable.",
                502,
            ) from None
        text = cap_text(final_ai_text(state["messages"]), self._settings.max_output_chars)
        return ChatAnswer(thread_id=public_id, message=text)


def build_chat_service(settings: Settings, model=None) -> ChatService:
    graph = build_graph(settings, build_checkpointer(settings), model=model)
    return ChatService(settings, graph, ThreadRegistry())
