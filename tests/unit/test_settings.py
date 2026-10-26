import os

import pytest
from pydantic import SecretStr, ValidationError

from chatbot_agent.core.config import Settings
from chatbot_agent.core.tracing import configure_tracing, redact_text
from tests.conftest import make_settings


def test_production_requires_auth_hosts_and_long_keys() -> None:
    with pytest.raises(ValidationError):
        make_settings(app_env="production")
    settings = make_settings(
        app_env="production",
        auth_enabled=True,
        api_keys=SecretStr("a" * 32 + ":service"),
        trusted_hosts="api.example.com",
        cors_origins="https://app.example.com",
    )
    assert settings.auth_enabled is True


def test_rejects_wildcard_cors_and_short_graph() -> None:
    with pytest.raises(ValidationError):
        make_settings(cors_origins="not a url")
    with pytest.raises(ValidationError):
        make_settings(max_graph_steps=4, max_tool_calls=3)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="test",
            model_provider="openai",
            model_name="gpt-4o-mini",
            model_api_key="",
            auth_enabled=False,
        )


def test_redact_text_and_tracing_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    assert redact_text("sk-abcdefghijklmnopqrstuvwxyz") == "[redacted]"
    assert redact_text("hello") == "hello"
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    configure_tracing(make_settings())
    assert os.environ["LANGSMITH_TRACING"] == "false"
