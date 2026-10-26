"""LangSmith tracing.

The default LangChain tracer is forced off. When tracing is enabled, a
request is traced only through a client that scrubs secret-shaped text.
If that client cannot be built, the request still runs and nothing is sent.
"""

import logging
import os
import re
from typing import Any

from chatbot_agent.core.config import Settings

logger = logging.getLogger(__name__)

_SECRET_TEXT = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}"
    r"|lsv2_[A-Za-z0-9_-]{8,}"
    r"|Bearer\s+[A-Za-z0-9._-]{8,}"
    r"|(?i:api[_-]?key|token|password|secret)\s*[:=]\s*\S+"
)


def redact_text(value: str) -> str:
    """Replace common key shapes and clip very long strings."""
    clipped = value if len(value) <= 8_000 else value[:8_000] + "..."
    return _SECRET_TEXT.sub("[redacted]", clipped)


def _redact_node(value: str, path: list[str | int]) -> str:
    del path
    return redact_text(value)


def configure_tracing(settings: Settings) -> None:
    """Turn off the process-wide tracer before LangChain reads it.

    Opt-in traces are started later, per request, with a redacting client.
    The API key stays on the settings object and is not copied into the
    environment by this function.
    """
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if not settings.langsmith_tracing:
        return
    logger.info("LangSmith tracing is enabled for project %s", settings.langsmith_project)


def invoke_with_optional_trace(graph: Any, payload: dict, config: dict, settings: Settings) -> Any:
    if not settings.langsmith_tracing:
        return graph.invoke(payload, config)
    try:
        from langsmith import Client, tracing_context
        from langsmith.anonymizer import create_anonymizer
    except Exception:
        logger.error("LangSmith could not be imported. This request will not be traced.")
        return graph.invoke(payload, config)

    client = Client(
        api_key=settings.langsmith_api_key.get_secret_value(),
        anonymizer=create_anonymizer(_redact_node),
    )
    with tracing_context(
        enabled=True,
        client=client,
        project_name=settings.langsmith_project,
    ):
        return graph.invoke(payload, config)
