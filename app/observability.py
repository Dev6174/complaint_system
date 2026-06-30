"""
Observability — Phase 6
-----------------------
Sentry error tracking + Prometheus metrics.
"""

import logging
import os

logger = logging.getLogger(__name__)


def init_sentry(app) -> None:
    from app.config import settings
    dsn = settings.SENTRY_DSN
    if not dsn:
        logger.info("Sentry disabled — SENTRY_DSN not set")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", "production"),
            traces_sample_rate=1.0 if os.getenv("APP_ENV") != "production" else 0.1,
            profiles_sample_rate=1.0,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialised (env=%s)", os.getenv("APP_ENV"))
    except ImportError:
        logger.warning("sentry-sdk not installed — skipping Sentry init")


def init_prometheus(app) -> None:  # noqa: ANN001
    """Mount Prometheus metrics at /metrics."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/metrics", "/health"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

        logger.info("Prometheus metrics exposed at /metrics")
    except ImportError:
        logger.warning(
            "prometheus-fastapi-instrumentator not installed — skipping Prometheus"
        )
