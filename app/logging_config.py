# pyrefly: ignore [missing-import]
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any

# Fields that must NEVER appear in logs
_SENSITIVE_FIELDS = {
    "password", "password_hash", "access_token", "csrf_token",
    "token", "secret", "authorization", "cookie",
}


class _SensitiveFilter(logging.Filter):
    """Strips known-sensitive keys from the log record's extra dict."""

    def filter(self, record: logging.LogRecord) -> bool:
        for field in list(vars(record).keys()):
            if field.lower() in _SENSITIVE_FIELDS:
                setattr(record, field, "***REDACTED***")
        return True


class _JsonFormatter(logging.Formatter):
    """Emits each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any structured extras attached by the caller
        standard_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                if key.lower() not in _SENSITIVE_FIELDS:
                    payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """
    Call once at application startup (in main.py).
    Sets up JSON structured logging for all complaint_system loggers.
    Third-party loggers (uvicorn, sqlalchemy) keep their default format
    to avoid excessive noise.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_SensitiveFilter())

    root_logger = logging.getLogger("complaint_system")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)
    root_logger.propagate = False
