import pytest
from langchain_core.messages import AIMessage

from chatbot_agent.agent.nodes import make_tools_node
from chatbot_agent.core.exceptions import AppError
from chatbot_agent.services.chat_service import build_chat_service
from tests.conftest import make_settings
from tests.helpers import ScriptedModel


def test_unknown_tool_is_rejected_before_it_runs() -> None:
    node = make_tools_node()
    result = node(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "shell",
                            "args": {"command": "ls"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                )
            ],
            "tool_calls_used": 0,
            "blocked": False,
        }
    )
    assert result["blocked"] is True
    assert "approved tools" in result["messages"][-1].content


def test_scripted_tool_call_returns_the_calculator_result() -> None:
    settings = make_settings(max_tool_calls=1, max_graph_steps=8)
    model = ScriptedModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "6*7"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="The product is 42."),
        ]
    )
    service = build_chat_service(settings, model=model)
    answer = service.reply("alice", "What is 6 * 7?", None, "req-1")
    assert answer.message == "The product is 42."


def test_tool_budget_stops_a_loop() -> None:
    settings = make_settings(max_tool_calls=1, max_graph_steps=8)
    model = ScriptedModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "1+1"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "1+1"},
                        "id": "call-2",
                        "type": "tool_call",
                    }
                ],
            ),
        ]
    )
    service = build_chat_service(settings, model=model)
    answer = service.reply("alice", "loop", None, "req-2")
    assert "tool-call limit" in answer.message
    assert model._replies == []


def test_threads_are_isolated_by_user() -> None:
    service = build_chat_service(make_settings(auth_enabled=False))
    first = service.reply("alice", "Hello", None, "req-1")
    service.reply("alice", "Hello again", first.thread_id, "req-2")
    saved = service.graph.get_state({"configurable": {"thread_id": f"alice:{first.thread_id}"}})
    assert len(saved.values["messages"]) >= 2
    other = service.graph.get_state({"configurable": {"thread_id": f"bob:{first.thread_id}"}})
    assert not other.values.get("messages")

    with pytest.raises(AppError) as denied:
        service.reply("bob", "Hello", first.thread_id, "req-3")
    assert denied.value.status_code == 403
