"""Errors that are safe to show to an API client."""


class AppError(Exception):
    """A known failure with a fixed client message.

    Do not put exception text, prompts, or secrets in ``message``. The HTTP
    handler returns ``code`` and ``message`` and nothing else.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}
