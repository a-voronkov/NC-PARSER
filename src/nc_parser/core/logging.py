from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def setup_structlog(level: str = "INFO") -> None:
    """Configure structlog for JSON logs."""
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer(to="message"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


