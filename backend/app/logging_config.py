"""
Structured logging setup for the Northstar API.

Configures a JSON-friendly formatter in production and a human-readable one
in development.  Import `get_logger` anywhere in the application code.
"""

import logging
import sys
from typing import Any

from app.config import get_settings

settings = get_settings()

_LOG_FORMAT_DEV = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_LOG_FORMAT_JSON = (
    '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}'
)


def configure_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    fmt = _LOG_FORMAT_DEV if settings.debug else _LOG_FORMAT_JSON

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpcore", "httpx", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class _RequestContextFilter(logging.Filter):
    """Injects request_id from context var into log records."""

    def filter(self, record: Any) -> bool:  # noqa: A003
        from app.middleware.request_id import get_request_id
        record.request_id = get_request_id()
        return True
