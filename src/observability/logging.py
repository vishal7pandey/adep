"""Structured logging with JSON and console formatters [BLK-130].

Provides:
- JSON formatter for production (machine-parseable)
- Console formatter for dev (human-readable with colors)
- Automatic context injection via contextvars
- PII redaction applied to all output

Configured via `ADE_LOG_FORMAT=json|console` (default: console).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.observability.context import get_context
from src.observability.redaction import redact_message


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter — one log record per line as a JSON object.

    Includes timestamp, level, logger name, message, and all context
    variables (request_id, run_id, etc.) plus any extra fields passed
    via `logger.info(msg, extra={...})`.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base fields
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_message(record.getMessage()),
        }

        # Inject context variables [BLK-130]
        ctx = get_context()
        log_entry.update(ctx)

        # Add extra fields from record.__dict__
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
            log_entry["exception_type"] = type(record.exc_info[1]).__name__

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter for local development.

    Format: ``LEVEL [logger] message  key=value key=value``

    Context variables are appended as key=value pairs for easy scanning.
    """

    # Colors for terminal output
    _COLORS = {
        "DEBUG": "\033[36m",    # cyan
        "INFO": "\033[32m",     # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",    # red
        "CRITICAL": "\033[35m", # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelname, "")
        reset = self._RESET if color else ""

        # Base message
        msg = redact_message(record.getMessage())

        # Context suffix
        ctx = get_context()
        ctx_str = "  ".join(f"{k}={v}" for k, v in ctx.items())
        if ctx_str:
            ctx_str = "  " + ctx_str

        # Extra fields
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        extras = []
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                extras.append(f"{key}={value}")
        extra_str = "  ".join(extras)
        if extra_str:
            extra_str = "  " + extra_str

        line = f"{color}{record.levelname:<7}{reset} [{record.name}] {msg}{ctx_str}{extra_str}"

        if record.exc_info and record.exc_info[1] is not None:
            line += f"\n{self.formatException(record.exc_info)}"

        return line


def configure_logging(format_type: str = "console", level: str = "INFO") -> None:
    """Configure the root logger with structured formatting [BLK-130].

    Args:
        format_type: "json" or "console" (from ADE_LOG_FORMAT).
        level: Logging level (from ADE_LOG_LEVEL or settings.log_level).
    """
    root = logging.getLogger()

    # Clear existing handlers to avoid duplicates on reconfigure
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    if format_type == "json":
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
