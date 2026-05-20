"""Servicios minimos para la sala de discusion sobre el esquema real."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


def get_threads_for_case(
    case_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista hilos activos asociados a un caso."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar hilos."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar hilos porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.table("discussion_threads")
            .select("*")
            .eq("case_id", str(case_id).strip())
            .eq("is_active", True)
            .order("sort_order")
            .order("created_at")
            .execute()
        )

        return True, result.data or [], "Hilos de discusion cargados correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar los hilos de discusion en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_interventions_for_thread(
    thread_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista intervenciones visibles de un hilo."""
    if not thread_id or not str(thread_id).strip():
        return False, [], "No se recibio un thread_id valido para consultar intervenciones."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar intervenciones porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_interventions_for_thread_secure",
                {"p_thread_id": str(thread_id).strip()},
            )
            .execute()
        )

        return True, result.data or [], "Intervenciones cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar las intervenciones en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def create_intervention(
    case_id: str,
    thread_id: str,
    author_id: str,
    role_id: str,
    intervention_type: str,
    content: str,
    parent_intervention_id: Optional[str] = None,
    phase: Optional[str] = None,
    title: Optional[str] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea una intervencion dentro de un hilo usando el esquema real."""
    if not case_id or not str(case_id).strip():
        return False, None, "No se recibio un case_id valido para publicar."

    if not thread_id or not str(thread_id).strip():
        return False, None, "No se recibio un thread_id valido para publicar."

    if not author_id or not str(author_id).strip():
        return False, None, "No se recibio un author_id valido para publicar."

    if not role_id or not str(role_id).strip():
        return False, None, "No se recibio un role_id valido para publicar."

    if not content or not str(content).strip():
        return False, None, "Debe escribir el contenido de la intervencion."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible publicar porque aun no hay credenciales validas "
            "de Supabase."
        )

    clean_content = str(content).strip()
    clean_type = str(intervention_type).strip()
    clean_title = str(title).strip() if title else clean_content[:80]

    try:
        result = (
            client.rpc(
                "create_intervention_secure",
                {
                    "p_case_id": str(case_id).strip(),
                    "p_thread_id": str(thread_id).strip(),
                    "p_author_id": str(author_id).strip(),
                    "p_role_id": str(role_id).strip(),
                    "p_parent_intervention_id": (
                        str(parent_intervention_id).strip()
                        if parent_intervention_id
                        else None
                    ),
                    "p_intervention_type": clean_type,
                    "p_title": clean_title,
                    "p_content": clean_content,
                    "p_phase": str(phase or "apertura").strip(),
                },
            )
            .execute()
        )
        rows = result.data or []
        saved_intervention = rows[0] if rows else {
            "case_id": str(case_id).strip(),
            "thread_id": str(thread_id).strip(),
            "author_id": str(author_id).strip(),
            "role_id": str(role_id).strip(),
            "parent_intervention_id": (
                str(parent_intervention_id).strip() if parent_intervention_id else None
            ),
            "intervention_type": clean_type,
            "title": clean_title,
            "content": clean_content,
            "phase": str(phase or "apertura").strip(),
            "is_visible": True,
        }

        return True, saved_intervention, "La intervencion fue publicada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible publicar la intervencion en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_student_participation_summary(
    case_id: str,
    author_id: str,
    role_id: str,
) -> Tuple[bool, Dict[str, int], str]:
    """Calcula un resumen minimo de participacion del estudiante."""
    empty_summary = {
        "interventions": 0,
        "responses": 0,
        "threads_used": 0,
    }

    if not case_id or not str(case_id).strip():
        return False, empty_summary, "No se recibio un case_id valido para el resumen."

    if not author_id or not str(author_id).strip():
        return False, empty_summary, "No se recibio un author_id valido para el resumen."

    if not role_id or not str(role_id).strip():
        return False, empty_summary, "No se recibio un role_id valido para el resumen."

    client = get_supabase_client()

    if client is None:
        return False, empty_summary, (
            "No fue posible consultar el resumen porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.table("interventions")
            .select("id, thread_id, parent_intervention_id")
            .eq("case_id", str(case_id).strip())
            .eq("author_id", str(author_id).strip())
            .eq("role_id", str(role_id).strip())
            .eq("is_visible", True)
            .execute()
        )

        rows = result.data or []
        threads_used = {
            row.get("thread_id")
            for row in rows
            if row.get("thread_id")
        }

        return True, {
            "interventions": len(rows),
            "responses": sum(1 for row in rows if row.get("parent_intervention_id")),
            "threads_used": len(threads_used),
        }, "Resumen de participacion cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, empty_summary, (
            "No fue posible consultar el resumen de participacion. "
            f"Detalle tecnico: {exc}"
        )


def get_case_discussion_summary(
    case_id: str,
) -> Tuple[bool, Dict[str, Any], str]:
    """Calcula un resumen minimo de discusion para un caso."""
    empty_summary = {
        "active_threads": 0,
        "total_interventions": 0,
        "interventions_by_author": {},
    }

    if not case_id or not str(case_id).strip():
        return False, empty_summary, "No se recibio un case_id valido para el resumen."

    client = get_supabase_client()

    if client is None:
        return False, empty_summary, (
            "No fue posible consultar el resumen porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        threads_result = (
            client.table("discussion_threads")
            .select("id")
            .eq("case_id", str(case_id).strip())
            .eq("is_active", True)
            .execute()
        )

        interventions_result = (
            client.table("interventions")
            .select("id, author_id")
            .eq("case_id", str(case_id).strip())
            .eq("is_visible", True)
            .execute()
        )

        threads = threads_result.data or []
        interventions = interventions_result.data or []
        by_author: Dict[str, int] = {}

        for intervention in interventions:
            author_id = intervention.get("author_id")
            if author_id:
                by_author[author_id] = by_author.get(author_id, 0) + 1

        return True, {
            "active_threads": len(threads),
            "total_interventions": len(interventions),
            "interventions_by_author": by_author,
        }, "Resumen de discusion del caso cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, empty_summary, (
            "No fue posible consultar el resumen de discusion del caso. "
            f"Detalle tecnico: {exc}"
        )
