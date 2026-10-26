"""Authentication and small request guards.

The API key list is one shared secret per user id. It is enough for a single
service client. It is not a user directory.
"""

import hashlib
import re
import secrets
import time
from collections import OrderedDict, deque
from dataclasses import dataclass

from chatbot_agent.core.exceptions import AppError

MAX_BODY_BYTES = 64 * 1024
_USER_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_MAX_KEYS = 10_000


@dataclass(frozen=True)
class User:
    user_id: str


def safe_log_value(value: object, limit: int = 200) -> str:
    """Keep log fields on one line and bounded."""
    text = str(value)
    cleaned = []
    for char in text[:limit]:
        if char.isprintable():
            cleaned.append(char)
        else:
            cleaned.append("?")
    return "".join(cleaned)


def secrets_equal(left: str, right: str) -> bool:
    """Compare secrets without leaking which character differed."""
    left_hash = hashlib.sha256(left.encode()).digest()
    right_hash = hashlib.sha256(right.encode()).digest()
    return secrets.compare_digest(left_hash, right_hash)


def parse_api_keys(raw: str) -> dict[str, str]:
    """Parse ``token:user_id`` pairs. The token is the secret."""
    keys: dict[str, str] = {}
    if not raw.strip():
        return keys
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        token, separator, user_id = entry.partition(":")
        if not separator or not token or not user_id:
            raise ValueError("API_KEYS entries must look like token:user_id.")
        if not _USER_ID.fullmatch(user_id):
            raise ValueError("API key user ids must be simple identifiers.")
        if token in keys:
            raise ValueError("API_KEYS contains a duplicate token.")
        keys[token] = user_id
    return keys


def authenticate(auth_enabled: bool, api_keys: dict[str, str], authorization: str | None) -> User:
    """Return the caller. Auth off always means the single local user."""
    if not auth_enabled:
        return User(user_id="local")

    if authorization is None or len(authorization) > 300:
        raise AppError("unauthorized", "Unauthorized.", 401)

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token or len(token) > 256:
        raise AppError("unauthorized", "Unauthorized.", 401)

    for stored, user_id in api_keys.items():
        if secrets_equal(token, stored):
            return User(user_id=user_id)
    raise AppError("unauthorized", "Unauthorized.", 401)


class RateLimiter:
    """Per-user sliding window. This counter is local to one process."""

    def __init__(self, limit_per_minute: int) -> None:
        self._limit = limit_per_minute
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, user_id: str) -> None:
        now = time.monotonic()
        hits = self._hits.get(user_id)
        if hits is None:
            if len(self._hits) >= _MAX_KEYS:
                self._hits.popitem(last=False)
            hits = deque()
            self._hits[user_id] = hits
        else:
            self._hits.move_to_end(user_id)

        while hits and now - hits[0] >= 60:
            hits.popleft()
        if len(hits) >= self._limit:
            raise AppError(
                "rate_limited",
                "Too many requests. Try again later.",
                429,
                {"Retry-After": "60"},
            )
        hits.append(now)
