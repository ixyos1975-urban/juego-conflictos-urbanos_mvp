"""Servicios minimos para consultar materiales de apoyo del caso."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


def get_case_materials_for_user(
    user_email: str,
    case_slug: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Consulta materiales activos del caso usando la RPC segura."""
    if not user_email or not str(user_email).strip():
        return False, [], "No se recibio un correo valido para consultar materiales."

    if not case_slug or not str(case_slug).strip():
        return False, [], "No se recibio un case_slug valido para consultar materiales."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar materiales porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_case_materials_secure",
                {
                    "p_user_email": str(user_email).strip().lower(),
                    "p_case_slug": str(case_slug).strip(),
                },
            )
            .execute()
        )

        return True, result.data or [], "Materiales del caso cargados correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar los materiales del caso en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_case_materials(
    user_email: str,
    case_slug: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Alias compatible para llamadas existentes."""
    return get_case_materials_for_user(user_email, case_slug)


def group_materials_by_type(
    materials: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Agrupa materiales por tipo para facilitar su renderizado en tabs."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for material in materials:
        material_type = str(material.get("material_type") or "otro").strip()
        grouped.setdefault(material_type, []).append(material)

    return grouped
