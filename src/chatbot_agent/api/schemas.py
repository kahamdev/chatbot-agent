"""Request and response bodies."""

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    thread_id: str | None = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message is empty.")
        if "\x00" in cleaned:
            raise ValueError("Message contains unsupported characters.")
        return cleaned


class ChatResponse(BaseModel):
    thread_id: str
    message: str
    request_id: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody
