"""Shared package constants and local configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

APP_DISPLAY_NAME = "Arctic Analytics"
DEFAULT_STREAMLIT_ENTRYPOINT = "arctic_analytics.streamlit_app"
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
SUPPORTED_OPENAI_MODELS = frozenset(
    {
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-6-astra",
    }
)
DEFAULT_ENV_PATH = Path(".env")


def validate_openai_model(model: str) -> str:
    """Return a supported model ID or reject an unsupported model override."""
    if model not in SUPPORTED_OPENAI_MODELS:
        supported_models = ", ".join(sorted(SUPPORTED_OPENAI_MODELS))
        raise ValueError(
            f"Model {model!r} is not supported. "
            f"Arctic Analytics only supports: {supported_models}."
        )
    return model


def load_runtime_config(env_path: Path | str = DEFAULT_ENV_PATH) -> dict[str, str]:
    """Load local runtime config from a simple .env file without mutating os.environ."""
    path = Path(env_path)
    if not path.exists():
        return {}

    config: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            config[key] = value
    return config


def get_config_value(
    key: str,
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
    session_state: Mapping[str, Any] | None = None,
    env_path: Path | str = DEFAULT_ENV_PATH,
    default: str | None = None,
) -> str | None:
    """Return config from .env, environment, Streamlit secrets, then session state."""
    env_file_value = load_runtime_config(env_path).get(key)
    if env_file_value:
        return env_file_value

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

    if session_state is not None:
        session_value = session_state.get(key)
        if session_value:
            return str(session_value)

    return default


def get_openai_api_key(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
    session_state: Mapping[str, Any] | None = None,
    env_path: Path | str = DEFAULT_ENV_PATH,
) -> str | None:
    if session_state is not None:
        session_value = session_state.get("OPENAI_API_KEY")
        if session_value and str(session_value).strip():
            return str(session_value).strip()

    env = os.environ if environ is None else environ
    for value in (load_runtime_config(env_path).get("OPENAI_API_KEY"), env.get("OPENAI_API_KEY")):
        if value and str(value).strip():
            return str(value).strip()

    if secrets is not None:
        try:
            value = secrets.get("OPENAI_API_KEY")
        except Exception:
            value = None
        if value and str(value).strip():
            return str(value).strip()
    return None


def has_openai_api_key(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
    session_state: Mapping[str, Any] | None = None,
    env_path: Path | str = DEFAULT_ENV_PATH,
) -> bool:
    return bool(
        get_openai_api_key(
            secrets=secrets,
            environ=environ,
            session_state=session_state,
            env_path=env_path,
        )
    )


def save_openai_api_key_to_env(
    api_key: str,
    env_path: Path | str = DEFAULT_ENV_PATH,
) -> Path:
    """Save the OpenAI key to a local .env file and restrict permissions when supported."""
    cleaned_key = api_key.strip()
    if not cleaned_key or "\n" in cleaned_key or "\r" in cleaned_key:
        raise ValueError("OpenAI API key cannot be empty or contain newlines.")

    path = Path(env_path)
    if path.is_symlink():
        raise RuntimeError(f"Refusing to write API key to symlinked path: {path}")

    existing = load_runtime_config(path)
    existing.setdefault("LLM_PROVIDER", "openai")
    existing["OPENAI_API_KEY"] = cleaned_key

    ordered_keys = ["LLM_PROVIDER", "OPENAI_API_KEY"]
    lines = [f"{key}={existing[key]}" for key in ordered_keys if key in existing]
    for key in sorted(set(existing) - set(ordered_keys)):
        lines.append(f"{key}={existing[key]}")

    try:
        _write_env_file(path, "\n".join(lines) + "\n")
    except OSError as exc:
        raise RuntimeError(f"Unable to write {path}.") from exc
    return path


def _write_env_file(path: Path, content: str) -> None:
    if os.name == "posix":
        _restrict_file_permissions(path)
        with open(path, "w", opener=lambda file, flags: os.open(file, flags, 0o600)) as handle:
            handle.write(content)
        _restrict_file_permissions(path)
        return

    path.write_text(content)
    _restrict_file_permissions(path)


def _restrict_file_permissions(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.chmod(0o600)
    except OSError:
        pass
