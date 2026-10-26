import pytest

from chatbot_agent.core.exceptions import AppError
from chatbot_agent.core.security import RateLimiter, authenticate, secrets_equal
from chatbot_agent.storage.threads import ThreadRegistry


def test_secrets_equal_does_not_accept_a_different_length() -> None:
    assert secrets_equal("test-key-alice", "test-key-alice")
    assert not secrets_equal("test-key-alice", "test-key-alic")
    assert not secrets_equal("test-key-alice", "test-key-bobxx")


def test_auth_failures_use_the_same_message() -> None:
    keys = {"test-key-alice": "alice"}
    user = authenticate(True, keys, "Bearer test-key-alice")
    assert user.user_id == "alice"
    assert authenticate(False, keys, None).user_id == "local"
    with pytest.raises(AppError) as missing:
        authenticate(True, keys, None)
    with pytest.raises(AppError) as wrong:
        authenticate(True, keys, "Bearer wrong-key")
    assert missing.value.message == wrong.value.message == "Unauthorized."


def test_rate_limit() -> None:
    limiter = RateLimiter(2)
    limiter.check("alice")
    limiter.check("alice")
    with pytest.raises(AppError) as limited:
        limiter.check("alice")
    assert limited.value.status_code == 429
    limiter.check("bob")


def test_thread_owner_and_uuid() -> None:
    registry = ThreadRegistry()
    created = registry.resolve("alice", None)
    assert registry.resolve("alice", created) == created
    with pytest.raises(AppError) as denied:
        registry.resolve("bob", created)
    assert denied.value.status_code == 403
    with pytest.raises(AppError) as invalid:
        registry.resolve("alice", "../secret")
    assert invalid.value.status_code == 400
