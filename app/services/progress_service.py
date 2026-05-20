"""Servicios para persistir el avance inicial del estudiante."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


PROGRESS_FIELDS = [
    "guide_completed",
    "case_context_completed",
    "role_preparation_completed",
    "public_actor_profile_completed",
]


def build_default_progress() -> Dict[str, bool]:
    """Devuelve el estado base del onboarding de estudiante."""
    return {
        "guide_completed": False,
        "case_context_completed": False,
        "role_preparation_completed": False,
        "public_actor_profile_completed": False,
    }


def get_student_progress(
    profile_id: str,
    case_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Lee el progreso persistido de un estudiante en un caso."""
    if not profile_id or not str(profile_id).strip():
        return False, None, "No se recibio un profile_id valido para consultar progreso."

    if not case_id or not str(case_id).strip():
        return False, None, "No se recibio un case_id valido para consultar progreso."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar progreso porque aun no hay credenciales "
            "validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_student_progress_secure",
                {
                    "p_profile_id": str(profile_id).strip(),
                    "p_case_id": str(case_id).strip(),
                },
            )
            .execute()
        )

        rows = result.data or []
        if not rows:
            return True, None, "No hay progreso persistido para este estudiante y caso."

        return True, rows[0], "Progreso del estudiante cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar progreso del estudiante en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def upsert_student_progress(
    profile_id: str,
    case_id: str,
    guide_completed: Optional[bool] = None,
    case_context_completed: Optional[bool] = None,
    role_preparation_completed: Optional[bool] = None,
    public_actor_profile_completed: Optional[bool] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea o actualiza parcialmente el progreso del onboarding."""
    if not profile_id or not str(profile_id).strip():
        return False, None, "No se recibio un profile_id valido para guardar progreso."

    if not case_id or not str(case_id).strip():
        return False, None, "No se recibio un case_id valido para guardar progreso."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible guardar progreso porque aun no hay credenciales "
            "validas de Supabase."
        )

    optional_fields = {
        "guide_completed": guide_completed,
        "case_context_completed": case_context_completed,
        "role_preparation_completed": role_preparation_completed,
        "public_actor_profile_completed": public_actor_profile_completed,
    }

    ok_current, current_progress, current_message = get_student_progress(
        profile_id,
        case_id,
    )

    if not ok_current:
        return False, None, current_message

    payload: Dict[str, Any] = build_default_progress()

    if current_progress:
        for field in PROGRESS_FIELDS:
            payload[field] = bool(current_progress.get(field, False))

    for field, value in optional_fields.items():
        if value is not None:
            payload[field] = bool(value)

    try:
        result = (
            client.rpc(
                "upsert_student_progress_secure",
                {
                    "p_profile_id": str(profile_id).strip(),
                    "p_case_id": str(case_id).strip(),
                    "p_guide_completed": payload["guide_completed"],
                    "p_case_context_completed": payload["case_context_completed"],
                    "p_role_preparation_completed": payload[
                        "role_preparation_completed"
                    ],
                    "p_public_actor_profile_completed": payload[
                        "public_actor_profile_completed"
                    ],
                },
            )
            .execute()
        )

        rows = result.data or []
        saved_progress = rows[0] if rows else payload

        return True, saved_progress, "Progreso del estudiante guardado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible guardar progreso del estudiante en Supabase. "
            f"Detalle tecnico: {exc}"
        )
