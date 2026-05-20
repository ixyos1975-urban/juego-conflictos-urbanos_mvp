"""Cliente base para Supabase."""

from __future__ import annotations

from typing import Optional

from supabase import Client, create_client

try:
    from config import settings
except ModuleNotFoundError:
    from app.config import settings


def get_supabase_client() -> Optional[Client]:
    """Devuelve un cliente de Supabase si existen credenciales válidas."""
    if not settings.has_supabase_credentials:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)
