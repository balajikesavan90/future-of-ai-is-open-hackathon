"""Shared package constants and local configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

APP_DISPLAY_NAME = "Arctic Analytics"
DEFAULT_STREAMLIT_ENTRYPOINT = "arctic_analytics.streamlit_app"


def get_config_value(
    key: str,
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
    default: str | None = None,
) -> str | None:
    """Return config from environment first, then Streamlit secrets if available."""
    env = os.environ if environ is None else environ
    env_value = env.get(key)
    if env_value:
        return env_value

    if secrets is not None:
        try:
            secret_value = secrets.get(key)
        except Exception:
            secret_value = None
        if secret_value:
            return str(secret_value)

    return default


def has_openai_api_key(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    return bool(get_config_value("OPENAI_API_KEY", secrets=secrets, environ=environ))
