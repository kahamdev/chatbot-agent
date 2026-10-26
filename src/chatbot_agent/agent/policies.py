"""Input and output limits shared by the API and the graph."""


def validate_user_message(text: str, max_chars: int) -> str | None:
    """Return a client-facing error, or None when the message can proceed."""
    if "\x00" in text:
        return "Please remove unsupported characters and try again."
    stripped = text.strip()
    if not stripped:
        return "Please send a message."
    if len(stripped) > max_chars:
        return "Please send a shorter message."
    return None


def cap_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def message_text(message: object) -> str:
    """Read model content whether it is a string or a list of text blocks."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        return "".join(parts)
    return str(content)


def final_ai_text(messages: list) -> str:
    """Last assistant message that is an answer, not a tool request."""
    from langchain_core.messages import AIMessage

    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            text = message_text(message).strip()
            if text:
                return text
    return "I could not produce a response."
