"""
Structured logging configuration for the FastAPI AI/Data Plane.

Outputs JSON-formatted log records so that log aggregation systems
(Loki, CloudWatch, Datadog, etc.) can parse fields without regex.
Falls back to readable text format if python-json-logger is unavailable.
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure application-wide structured JSON logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    try:
        from pythonjsonlogger import json as jsonlogger  # type: ignore[import-untyped]

        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logging.root.setLevel(log_level)
        logging.root.handlers = [handler]
    except ImportError:
        # python-json-logger not installed — use readable text format as fallback.
        # Add python-json-logger to requirements.txt to enable JSON output.
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


logger = logging.getLogger("fastapi_backend")
