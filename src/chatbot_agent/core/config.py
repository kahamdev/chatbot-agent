"""Environment-backed settings.

Values passed to the constructor win over the process environment, which
keeps tests isolated. Secrets use ``SecretStr`` so logs do not print them.
"""

import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_PREFIX = re.compile(r"^/[A-Za-z0-9/_-]{1,64}$")
_HOST = re.compile(r"[A-Za-z0-9.:-]{1,255}")
_TRUSTED_HOST = re.compile(r"[A-Za-z0-9.*:-]{1,255}")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "chatbot-agent"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    model_provider: Literal["local", "openai"] = "local"
    model_name: str = "local"
    model_api_key: SecretStr = SecretStr("")
    model_temperature: float = Field(default=0, ge=0, le=1)
    model_timeout_seconds: int = Field(default=30, ge=1, le=120)

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "chatbot-agent-dev"

    checkpoint_backend: Literal["memory"] = "memory"

    auth_enabled: bool = False
    api_keys: SecretStr = SecretStr("")
    cors_origins: str = "http://localhost:3000"
    trusted_hosts: str = ""
    rate_limit_per_minute: int = Field(default=30, ge=1, le=600)

    max_request_chars: int = Field(default=8000, ge=1, le=32_000)
    max_output_tokens: int = Field(default=1200, ge=1, le=4000)
    max_graph_steps: int = Field(default=12, ge=4, le=50)
    max_tool_calls: int = Field(default=3, ge=1, le=10)
    tool_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @property
    def max_output_chars(self) -> int:
        """Character stand-in for the token budget. No tokenizer required."""
        return min(self.max_output_tokens * 4, 20_000)

    @property
    def parsed_api_keys(self) -> dict[str, str]:
        return parse_keys(self.api_keys.get_secret_value())

    @property
    def cors_origin_list(self) -> list[str]:
        return _csv(self.cors_origins)

    @property
    def trusted_host_list(self) -> list[str]:
        return _csv(self.trusted_hosts)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("app_name")
    @classmethod
    def check_app_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
            raise ValueError("APP_NAME must be a short identifier.")
        return value

    @field_validator("api_prefix")
    @classmethod
    def check_prefix(cls, value: str) -> str:
        if not _API_PREFIX.fullmatch(value) or value.endswith("/"):
            raise ValueError("API_PREFIX must be a short absolute path.")
        return value

    @field_validator("host")
    @classmethod
    def check_host(cls, value: str) -> str:
        if not _HOST.fullmatch(value):
            raise ValueError("HOST is invalid.")
        return value

    @field_validator("model_name", "langsmith_project")
    @classmethod
    def check_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
            raise ValueError("Expected a short identifier without spaces.")
        return value

    @model_validator(mode="after")
    def check_runtime_rules(self) -> "Settings":
        if self.model_provider == "openai":
            if not self.model_api_key.get_secret_value().strip():
                raise ValueError("MODEL_API_KEY is required when MODEL_PROVIDER=openai.")
            if self.model_name == "local":
                raise ValueError("Set MODEL_NAME when MODEL_PROVIDER=openai.")

        minimum_steps = self.max_tool_calls * 2 + 4
        if self.max_graph_steps < minimum_steps:
            raise ValueError(
                f"MAX_GRAPH_STEPS is too small for MAX_TOOL_CALLS. Use at least {minimum_steps}."
            )

        self._check_origins()
        self._check_hosts()
        self._check_keys()
        if self.langsmith_tracing and not self.langsmith_api_key.get_secret_value().strip():
            raise ValueError("LANGSMITH_API_KEY is required when tracing is enabled.")
        if self.app_env == "production":
            self._check_production()
        return self

    def _check_origins(self) -> None:
        for origin in self.cors_origin_list:
            if origin == "*":
                continue
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.username
                or parsed.password
            ):
                raise ValueError("CORS_ORIGINS contains an invalid origin.")

    def _check_hosts(self) -> None:
        for host in self.trusted_host_list:
            if not _TRUSTED_HOST.fullmatch(host):
                raise ValueError("TRUSTED_HOSTS contains an invalid host.")

    def _check_keys(self) -> None:
        # Import locally so config can be read without pulling auth into a cycle.
        from chatbot_agent.core.security import parse_api_keys

        keys = parse_api_keys(self.api_keys.get_secret_value())
        if self.auth_enabled and not keys:
            raise ValueError("API_KEYS is required when AUTH_ENABLED=true.")
        minimum = 32 if self.app_env == "production" else 8
        for token in keys:
            if len(token) < minimum or any(char.isspace() for char in token):
                raise ValueError("An API key is too short or contains spaces.")

    def _check_production(self) -> None:
        if not self.auth_enabled:
            raise ValueError("AUTH_ENABLED must be true in production.")
        if not self.trusted_host_list or "*" in self.trusted_host_list:
            raise ValueError("Set explicit TRUSTED_HOSTS in production.")
        if not self.cors_origin_list or "*" in self.cors_origin_list:
            raise ValueError("Set explicit CORS_ORIGINS in production.")


def parse_keys(raw: str) -> dict[str, str]:
    from chatbot_agent.core.security import parse_api_keys

    return parse_api_keys(raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
