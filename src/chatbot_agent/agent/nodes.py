"""One function per graph step.

The steps are plain Python. The graph module decides the order.
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from chatbot_agent.agent.policies import cap_text, message_text, validate_user_message
from chatbot_agent.agent.prompts import SYSTEM_PROMPT
from chatbot_agent.agent.state import ChatState
from chatbot_agent.core.config import Settings
from chatbot_agent.tools.registry import allowed_tool_names, list_tools

_TOOL_OUTPUT_CHARS = 1000


def make_validate_input(settings: Settings):
    def validate_input(state: ChatState) -> dict:
        human = next(
            (
                message
                for message in reversed(state["messages"])
                if isinstance(message, HumanMessage)
            ),
            None,
        )
        if human is None:
            return _block("Please send a message.")
        problem = validate_user_message(message_text(human), settings.max_request_chars)
        if problem:
            return _block(problem)
        return {"blocked": False}

    return validate_input


def make_assistant(model):
    tools = list_tools()

    def assistant(state: ChatState) -> dict:
        if state.get("blocked"):
            return {}
        # The tool budget is enforced by routing. This step can still write
        # the final answer after the last allowed tool has run.
        history = list(state["messages"])
        prefix: list = []
        if not any(isinstance(message, SystemMessage) for message in history):
            prefix = [SystemMessage(content=SYSTEM_PROMPT)]
        response = model.bind_tools(tools).invoke([*prefix, *history])
        if not isinstance(response, AIMessage):
            response = AIMessage(content=message_text(response))
        return {"messages": [*prefix, response]}

    return assistant


def make_tools_node():
    allowed = allowed_tool_names()
    runner = ToolNode(list_tools(), handle_tool_errors=True)

    def tools_node(state: ChatState) -> dict:
        last = state["messages"][-1]
        calls = list(getattr(last, "tool_calls", []) or [])
        used = int(state.get("tool_calls_used", 0))
        if not calls:
            return {"tool_calls_used": used}
        if any(call["name"] not in allowed for call in calls):
            denied: list = [
                ToolMessage(
                    content="That tool is not available.",
                    tool_call_id=str(call["id"]),
                    name=str(call["name"]),
                )
                for call in calls
            ]
            denied.append(AIMessage(content="I can only use the approved tools."))
            return {
                "messages": denied,
                "tool_calls_used": used + len(calls),
                "blocked": True,
            }
        result = runner.invoke({"messages": state["messages"]})
        capped: list = []
        for message in result.get("messages", []):
            if isinstance(message, ToolMessage):
                capped.append(
                    message.model_copy(
                        update={"content": cap_text(message_text(message), _TOOL_OUTPUT_CHARS)}
                    )
                )
            else:
                capped.append(message)
        return {"messages": capped, "tool_calls_used": used + len(calls)}

    return tools_node


def make_finalize(settings: Settings):
    def finalize(state: ChatState) -> dict:
        if not state["messages"]:
            return {"messages": [AIMessage(content="I could not produce a response.")]}
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            notes: list = [
                ToolMessage(
                    content="This tool call was not run because the limit was reached.",
                    tool_call_id=str(call["id"]),
                    name=str(call["name"]),
                )
                for call in last.tool_calls
            ]
            notes.append(AIMessage(content="I reached the tool-call limit for this turn."))
            return {"messages": notes}
        if isinstance(last, AIMessage):
            text = cap_text(message_text(last), settings.max_output_chars)
            if text == message_text(last):
                return {}
            if last.id:
                return {"messages": [last.model_copy(update={"content": text})]}
            return {"messages": [AIMessage(content=text)]}
        return {"messages": [AIMessage(content="I could not produce a response.")]}

    return finalize


def route_after_validation(state: ChatState) -> str:
    if state.get("blocked"):
        return "finalize"
    return "assistant"


def route_after_assistant(state: ChatState, max_tool_calls: int) -> str:
    if state.get("blocked"):
        return "finalize"
    last = state["messages"][-1]
    calls = list(getattr(last, "tool_calls", []) or [])
    used = int(state.get("tool_calls_used", 0))
    if calls and used + len(calls) <= max_tool_calls:
        return "tools"
    return "finalize"


def route_after_tools(state: ChatState) -> str:
    if state.get("blocked"):
        return "finalize"
    return "assistant"


def _block(text: str) -> dict:
    return {"blocked": True, "messages": [AIMessage(content=text)]}
