"""Which user owns a conversation id.

The checkpoint key is ``user_id:thread_id``, so one user cannot read another
user's saved messages by guessing the public id. This map also rejects that
guess with 403 instead of starting an empty twin conversation.
"""

import uuid
from collections import OrderedDict

from chatbot_agent.core.exceptions import AppError

_MAX_THREADS = 10_000


class ThreadRegistry:
    def __init__(self) -> None:
        self._owners: OrderedDict[str, str] = OrderedDict()

    def resolve(self, user_id: str, thread_id: str | None) -> str:
        if thread_id is None:
            return self._claim(user_id, str(uuid.uuid4()))
        try:
            public_id = str(uuid.UUID(thread_id))
        except ValueError:
            raise AppError("invalid_thread", "Thread id must be a UUID.", 400) from None
        owner = self._owners.get(public_id)
        if owner is None:
            return self._claim(user_id, public_id)
        if owner != user_id:
            raise AppError("forbidden", "You cannot access this conversation.", 403)
        self._owners.move_to_end(public_id)
        return public_id

    def _claim(self, user_id: str, public_id: str) -> str:
        if public_id not in self._owners and len(self._owners) >= _MAX_THREADS:
            raise AppError("unavailable", "The server cannot start another conversation.", 503)
        self._owners[public_id] = user_id
        self._owners.move_to_end(public_id)
        return public_id
