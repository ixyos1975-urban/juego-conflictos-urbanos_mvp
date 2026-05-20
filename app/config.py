"""Configuración base de la app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=False)
ENV_VALUES = dotenv_values(ENV_PATH)

try:
    import streamlit as st
except Exception:  # noqa: BLE001
    st = None  # type: ignore[assignment]


def _clean_config_value(value: object) -> str:
    return str(value or "").strip().strip('"').strip("'")


def _get_secret_value(name: str) -> object:
    if st is None:
        return None

    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # noqa: BLE001
        return None

    return None


def _get_config(name: str, default: str = "", *aliases: str) -> str:
    for key in (name, *aliases):
        secret_value = _get_secret_value(key)
        if secret_value not in (None, ""):
            return _clean_config_value(secret_value)

    for key in (name, *aliases):
        env_value = os.environ.get(key)
        if env_value not in (None, ""):
            return _clean_config_value(env_value)

    for key in (name, *aliases):
        dotenv_value = ENV_VALUES.get(key)
        if dotenv_value not in (None, ""):
            return _clean_config_value(dotenv_value)

    return default


def _get_bool_config(name: str, default: str = "false", *aliases: str) -> bool:
    """Lee booleanos tolerando comillas y valores comunes."""
    value = _get_config(name, default, *aliases).lower()
    return value in {"true", "1", "yes", "on"}


def _get_int_config(name: str, default: str, *aliases: str) -> int:
    try:
        return int(_get_config(name, default, *aliases))
    except ValueError:
        return int(default)


def _get_float_config(name: str, default: str, *aliases: str) -> float:
    try:
        return float(_get_config(name, default, *aliases))
    except ValueError:
        return float(default)


@dataclass(frozen=True)
class Settings:
    app_title: str = _get_config("APP_TITLE", "Juego de conflictos urbanos MVP")
    supabase_url: str = _get_config("SUPABASE_URL")
    supabase_key: str = _get_config("SUPABASE_KEY")
    default_case_slug: str = _get_config("DEFAULT_CASE_SLUG")
    allowed_email_domain: str = _get_config(
        "ALLOWED_EMAIL_DOMAIN",
        "unisalle.edu.co",
    )
    ai_enabled: bool = _get_bool_config("AI_ENABLED")
    ai_provider: str = _get_config("AI_PROVIDER", "deepseek")
    ai_api_key: str = _get_config("AI_API_KEY")
    ai_base_url: str = _get_config(
        "AI_BASE_URL",
        "https://api.deepseek.com",
        "AI_API_URL",
    )
    ai_api_url: str = ai_base_url
    ai_model: str = _get_config("AI_MODEL", "deepseek-v4-flash")
    ai_timeout_seconds: int = _get_int_config("AI_TIMEOUT_SECONDS", "30")
    ai_max_tokens: int = _get_int_config("AI_MAX_TOKENS", "1200")
    ai_temperature: float = _get_float_config("AI_TEMPERATURE", "0.2")
    ai_prompt_version: str = _get_config("AI_PROMPT_VERSION", "ai_review_v1")

    @property
    def has_supabase_credentials(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


settings = Settings()
