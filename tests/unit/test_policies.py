from langchain_core.messages import AIMessage

from chatbot_agent.agent.policies import cap_text, final_ai_text, validate_user_message


def test_message_limits() -> None:
    assert validate_user_message("   ", 10) == "Please send a message."
    assert validate_user_message("hello\x00", 10) is not None
    assert "shorter" in (validate_user_message("hello there", 5) or "")
    assert validate_user_message("hello", 5) is None


def test_cap_and_final_answer() -> None:
    assert cap_text("abcdef", 3) == "abc..."
    messages = [
        AIMessage(
            content="",
            tool_calls=[{"name": "calculator", "args": {}, "id": "1", "type": "tool_call"}],
        ),
        AIMessage(content="The result is 4."),
    ]
    assert final_ai_text(messages) == "The result is 4."
