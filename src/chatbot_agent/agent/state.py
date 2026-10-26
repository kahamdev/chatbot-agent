"""State carried through one conversation thread."""

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ChatState(TypedDict):
    """Messages append. The other fields are replaced on each update.

    ``tool_calls_used`` and ``blocked`` are reset by the chat service at the
    start of every user turn.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    tool_calls_used: int
    blocked: bool
