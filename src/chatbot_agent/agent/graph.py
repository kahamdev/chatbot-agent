"""How a turn moves through the agent.

    validate_input -> assistant -> tools -> assistant -> ... -> finalize

The assistant may ask for a tool. The tools step runs only names on the
allowlist. The loop stops when there is no tool call, the tool budget is
spent, or the step limit is reached.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chatbot_agent.agent.model import build_model
from chatbot_agent.agent.nodes import (
    make_assistant,
    make_finalize,
    make_tools_node,
    make_validate_input,
    route_after_assistant,
    route_after_tools,
    route_after_validation,
)
from chatbot_agent.agent.state import ChatState
from chatbot_agent.core.config import Settings


def build_graph(
    settings: Settings,
    checkpointer: BaseCheckpointSaver,
    model=None,
) -> CompiledStateGraph:
    chat_model = model if model is not None else build_model(settings)
    graph = StateGraph(ChatState)
    graph.add_node("validate_input", make_validate_input(settings))
    graph.add_node("assistant", make_assistant(chat_model))
    graph.add_node("tools", make_tools_node())
    graph.add_node("finalize", make_finalize(settings))

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"assistant": "assistant", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "assistant",
        lambda state: route_after_assistant(state, settings.max_tool_calls),
        {"tools": "tools", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {"assistant": "assistant", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)
