"""Shared settings for tests. Constructor values override the environment."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from chatbot_agent.core.config import Settings
from chatbot_agent.main import create_app


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "test",
        "auth_enabled": True,
        "api_keys": SecretStr("test-key-alice:alice,test-key-bob:bob"),
        "model_provider": "local",
        "model_name": "local",
        "langsmith_tracing": False,
        "rate_limit_per_minute": 60,
        "trusted_hosts": "",
        "cors_origins": "http://localhost:3000",
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client


def auth_header(user: str = "alice") -> dict[str, str]:
    token = "test-key-alice" if user == "alice" else "test-key-bob"
    return {"Authorization": f"Bearer {token}"}
