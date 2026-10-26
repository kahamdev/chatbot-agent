"""Conversation memory for this process.

MemorySaver is cleared on restart and is not shared by multiple workers.
A durable backend needs its own owner records. Do not store a thread under
an id the client supplied without the user prefix applied in the service.
"""

from langgraph.checkpoint.memory import MemorySaver

from chatbot_agent.core.config import Settings


def build_checkpointer(settings: Settings) -> MemorySaver:
    if settings.checkpoint_backend != "memory":
        raise RuntimeError("Only CHECKPOINT_BACKEND=memory is supported.")
    return MemorySaver()
