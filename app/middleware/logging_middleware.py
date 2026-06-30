"""
Structured JSON logging middleware — Phase 6
--------------------------------------------
Emits one JSON log line per request.
"""

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.access")


def configure_json_logging() -> None:
    """Switch the root logger to JSON output. Skips reconfiguration in tests."""
    import os

    if os.getenv("APP_ENV") == "test":
        return

    try:
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        logger.info("JSON logging configured")
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        logger.warning("python-json-logger not installed — using plain text logs")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request as a structured JSON line."""

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "ip": _get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
        }

        if duration_ms > 1000:
            logger.warning("slow request", extra=log_data)
        elif response.status_code >= 500:
            logger.error("server error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("client error", extra=log_data)
        else:
            logger.info("request completed", extra=log_data)

        response.headers["X-Request-ID"] = request_id
        return response


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"