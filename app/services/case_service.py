"""Servicios básicos de lectura del caso para el MVP.

Este servicio centraliza la lectura del caso activo desde Supabase,
para que las pantallas no repitan consultas ni lógica de validación.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

# Import flexible para que el archivo funcione tanto si la app corre
# desde la carpeta `app/` como si se ejecuta como paquete.
try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


COLOMBIA_TZ = timezone(timedelta(hours=-5), name="America/Bogota")
CASE_INTERACTION_CLOSES_AT = datetime(2026, 5, 30, 23, 59, tzinfo=COLOMBIA_TZ)
CASE_CLOSED_STATUSES = {
    "closed",
    "cerrado",
    "cerrada",
    "finalizado",
    "finalizada",
    "archived",
    "archivado",
    "archivada",
}


def _safe_float(value: Any) -> Optional[float]:
    """Convierte valores numericos de Supabase a float cuando es posible."""
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_case_interaction_closed(case_record: Optional[Dict[str, Any]]) -> bool:
    """Indica si el estudiante debe quedar en modo solo lectura."""
    if is_case_status_closed(case_record):
        return True

    return datetime.now(COLOMBIA_TZ) >= CASE_INTERACTION_CLOSES_AT


def is_case_status_closed(case_record: Optional[Dict[str, Any]]) -> bool:
    """Indica si el caso fue cerrado formalmente por su estado persistido."""
    case_record = case_record or {}
    status = str(case_record.get("status") or "").strip().lower()

    return status in CASE_CLOSED_STATUSES


def get_case_by_slug(case_slug: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca un caso por su slug."""
    if not case_slug or not str(case_slug).strip():
        return False, None, "No se recibió un case_slug válido."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar el caso porque aún no hay "
            "credenciales válidas de Supabase."
        )

    try:
        result = (
            client.table("cases")
            .select("*")
            .eq("slug", str(case_slug).strip())
            .limit(1)
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, "No se encontró un caso asociado al slug recibido."

        return True, rows[0], "Caso encontrado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar el caso en Supabase. "
            f"Detalle técnico: {exc}"
        )


def get_case_slug_for_user(email: str) -> Tuple[bool, Optional[str], str]:
    """Busca en `allowed_users` el case_slug asociado al usuario."""
    if not email or not str(email).strip():
        return False, None, "No se recibió un correo válido."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar el usuario porque aún no hay "
            "credenciales válidas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_allowed_user_by_email_secure",
                {"p_email": str(email).strip().lower()},
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, "El usuario no aparece en la tabla allowed_users."

        record = rows[0]

        if not record.get("is_active", True):
            return False, None, "El usuario fue encontrado, pero no está activo."

        case_slug = record.get("case_slug")

        if not case_slug:
            return False, None, (
                "El usuario fue encontrado, pero no tiene case_slug asignado."
            )

        return True, str(case_slug).strip(), "case_slug encontrado para el usuario."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar el case_slug del usuario. "
            f"Detalle técnico: {exc}"
        )


def get_case_for_user(email: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Resuelve el caso activo de un usuario a partir de su correo.

    Orden:
    1. busca case_slug en allowed_users;
    2. busca el caso correspondiente en cases.
    """
    ok_slug, case_slug, message_slug = get_case_slug_for_user(email)
    if not ok_slug:
        return False, None, message_slug

    return get_case_by_slug(case_slug)


def build_case_context(case_record: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte el registro bruto del caso en una estructura más cómoda."""
    return {
        "id": case_record.get("id"),
        "slug": case_record.get("slug"),
        "title": case_record.get("title") or "Caso sin título",
        "description": case_record.get("description") or "",
        "territorial_context": case_record.get("territorial_context") or "",
        "location_name": case_record.get("location_name") or "",
        "phase": case_record.get("phase") or "No definida",
        "status": case_record.get("status") or "No definido",
        "rules": case_record.get("rules") or "",
        "evaluation_criteria": case_record.get("evaluation_criteria") or "",
        "map_center_lat": _safe_float(case_record.get("map_center_lat")),
        "map_center_lng": _safe_float(case_record.get("map_center_lng")),
        "geojson_data": case_record.get("geojson_data"),
    }


def get_case_context_for_user(email: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Devuelve una versión lista para interfaz del caso activo del usuario."""
    ok_case, case_record, message_case = get_case_for_user(email)
    if not ok_case or case_record is None:
        return False, None, message_case

    return True, build_case_context(case_record), "Contexto del caso preparado correctamente."
