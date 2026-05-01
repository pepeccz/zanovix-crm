"""
Zanovix CRM — Shared utilities module.
"""

from shared.config import Settings, get_settings
from shared.logging_config import configure_logging
from shared.redis_client import get_redis_client
from shared.errors import (
    ErrorCategory,
    APIErrorResponse,
    ErrorLogger,
    get_error_logger,
    map_status_to_category,
    translate_to_spanish,
)
from shared.fastapi_errors import register_error_handlers

__all__ = [
    "Settings",
    "get_settings",
    "configure_logging",
    "get_redis_client",
    "ErrorCategory",
    "APIErrorResponse",
    "ErrorLogger",
    "get_error_logger",
    "map_status_to_category",
    "translate_to_spanish",
    "register_error_handlers",
]
