"""Servicio para persistir el perfil publico del actor."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


PROFILE_FIELDS = [
    "display_name",
    "avatar_url",
    "public_presentation",
    "initial_position",
    "main_interest",
    "non_negotiable_point",
    "action_line",
]

REFERENCE_FIELDS = [
    "allowed_user_id",
    "case_id",
    "role_id",
]

STATUS_FIELDS = [
    "profile_status",
    "submitted_at",
]


def build_empty_profile() -> Dict[str, str]:
    """Devuelve la estructura base del perfil usada por la interfaz."""
    return {
        **{field: "" for field in PROFILE_FIELDS},
        "profile_status": "draft",
        "submitted_at": "",
    }


def normalize_profile_data(profile_data: Dict[str, Any]) -> Dict[str, str]:
    """Limpia y limita el diccionario a los campos persistibles."""
    return {
        **{
            field: str(profile_data.get(field) or "").strip()
            for field in PROFILE_FIELDS
        },
        "profile_status": str(profile_data.get("profile_status") or "draft").strip(),
        "submitted_at": str(profile_data.get("submitted_at") or "").strip(),
    }


def normalize_reference_data(profile_data: Dict[str, Any]) -> Dict[str, str]:
    """Incluye IDs preparatorios solo si vienen informados."""
    return {
        field: str(profile_data.get(field)).strip()
        for field in REFERENCE_FIELDS
        if profile_data.get(field)
    }


def get_profile_for_user_case(
    user_email: str,
    case_slug: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca el perfil publico de un usuario dentro de un caso."""
    if not user_email or not str(user_email).strip():
        return False, None, "No se recibio un correo valido para consultar el perfil."

    if not case_slug or not str(case_slug).strip():
        return False, None, "No se recibio un case_slug valido para consultar el perfil."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar el perfil porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_actor_profile_secure",
                {
                    "p_user_email": str(user_email).strip().lower(),
                    "p_case_slug": str(case_slug).strip(),
                },
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return True, None, "No existe un perfil publico guardado todavia."

        return True, rows[0], "Perfil publico cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar el perfil publico en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def upsert_profile_for_user_case(
    user_email: str,
    case_slug: str,
    profile_data: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea o actualiza el perfil publico usando user_email + case_slug."""
    if not user_email or not str(user_email).strip():
        return False, None, "No se recibio un correo valido para guardar el perfil."

    if not case_slug or not str(case_slug).strip():
        return False, None, "No se recibio un case_slug valido para guardar el perfil."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible guardar el perfil porque aun no hay "
            "credenciales validas de Supabase."
        )

    clean_profile = normalize_profile_data(profile_data)

    try:
        result = (
            client.rpc(
                "upsert_actor_profile_secure",
                {
                    "p_user_email": str(user_email).strip().lower(),
                    "p_case_slug": str(case_slug).strip(),
                    "p_display_name": clean_profile["display_name"],
                    "p_avatar_url": clean_profile["avatar_url"],
                    "p_public_presentation": clean_profile["public_presentation"],
                    "p_initial_position": clean_profile["initial_position"],
                    "p_main_interest": clean_profile["main_interest"],
                    "p_non_negotiable_point": clean_profile["non_negotiable_point"],
                    "p_action_line": clean_profile["action_line"],
                },
            )
            .execute()
        )

        rows = result.data or []
        saved_record = rows[0] if rows else {
            "user_email": str(user_email).strip().lower(),
            "case_slug": str(case_slug).strip(),
            **clean_profile,
        }

        return True, saved_record, "Perfil publico del actor guardado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible guardar el perfil publico en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def submit_profile_for_user_case(
    user_email: str,
    case_slug: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Marca el perfil publico como enviado definitivamente."""
    if not user_email or not str(user_email).strip():
        return False, None, "No se recibio un correo valido para enviar el perfil."

    if not case_slug or not str(case_slug).strip():
        return False, None, "No se recibio un case_slug valido para enviar el perfil."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible enviar el perfil porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "submit_actor_profile_secure",
                {
                    "p_user_email": str(user_email).strip().lower(),
                    "p_case_slug": str(case_slug).strip(),
                },
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, "No fue posible confirmar el envio definitivo del perfil."

        return True, rows[0], "Perfil publico enviado definitivamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible enviar el perfil publico en Supabase. "
            f"Detalle tecnico: {exc}"
        )
