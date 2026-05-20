"""Servicios minimos para evidencias sobre el esquema real."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


def get_interventions_available_for_evidence(
    case_id: str,
    author_id: str,
    role_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista intervenciones reales del estudiante que pueden recibir evidencia."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar intervenciones."

    if not author_id or not str(author_id).strip():
        return False, [], "No se recibio un author_id valido para consultar intervenciones."

    if not role_id or not str(role_id).strip():
        return False, [], "No se recibio un role_id valido para consultar intervenciones."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar intervenciones porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.table("interventions")
            .select("*, discussion_threads(title)")
            .eq("case_id", str(case_id).strip())
            .eq("author_id", str(author_id).strip())
            .eq("role_id", str(role_id).strip())
            .eq("is_visible", True)
            .order("created_at", desc=True)
            .execute()
        )

        rows = result.data or []
        for row in rows:
            thread = row.get("discussion_threads") or {}
            row["thread_title"] = thread.get("title") or "Hilo sin título"

        return True, rows, "Intervenciones disponibles cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar intervenciones en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_evidences_for_user(
    uploaded_by: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista evidencias cargadas por un perfil."""
    if not uploaded_by or not str(uploaded_by).strip():
        return False, [], "No se recibio un uploaded_by valido para consultar evidencias."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar evidencias porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_evidences_for_user_secure",
                {"p_uploaded_by": str(uploaded_by).strip()},
            )
            .execute()
        )

        return True, result.data or [], "Evidencias cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar evidencias en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def create_evidence(
    intervention_id: str,
    uploaded_by: str,
    evidence_type: str,
    title: str,
    description: str,
    reference_text: str,
    external_url: str,
    file_url: Optional[str] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea una evidencia asociada a una intervencion real."""
    if not intervention_id or not str(intervention_id).strip():
        return False, None, "Debe seleccionar una intervencion para asociar la evidencia."

    if not uploaded_by or not str(uploaded_by).strip():
        return False, None, "No se recibio un uploaded_by valido para guardar evidencia."

    if not title or not str(title).strip():
        return False, None, "Debe ingresar al menos un titulo breve para la evidencia."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible guardar la evidencia porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "create_evidence_secure",
                {
                    "p_intervention_id": str(intervention_id).strip(),
                    "p_uploaded_by": str(uploaded_by).strip(),
                    "p_evidence_type": str(evidence_type).strip(),
                    "p_title": str(title).strip(),
                    "p_description": str(description or "").strip(),
                    "p_reference_text": str(reference_text or "").strip(),
                    "p_external_url": str(external_url or "").strip(),
                    "p_file_url": str(file_url).strip() if file_url else "",
                },
            )
            .execute()
        )
        rows = result.data or []
        saved_evidence = rows[0] if rows else {
            "intervention_id": str(intervention_id).strip(),
            "uploaded_by": str(uploaded_by).strip(),
            "evidence_type": str(evidence_type).strip(),
            "title": str(title).strip(),
            "description": str(description or "").strip(),
            "reference_text": str(reference_text or "").strip(),
            "external_url": str(external_url or "").strip(),
            "file_url": str(file_url).strip() if file_url else None,
        }

        return True, saved_evidence, "La evidencia fue guardada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible guardar la evidencia en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_evidence_counts_for_case(
    case_id: str,
) -> Tuple[bool, Dict[str, Any], str]:
    """Cuenta evidencias del caso y las agrupa por autor de la intervencion."""
    empty_summary = {
        "total_evidences": 0,
        "evidences_by_author": {},
    }

    if not case_id or not str(case_id).strip():
        return False, empty_summary, "No se recibio un case_id valido para contar evidencias."

    client = get_supabase_client()

    if client is None:
        return False, empty_summary, (
            "No fue posible consultar evidencias porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_evidence_counts_for_case_secure",
                {"p_case_id": str(case_id).strip()},
            )
            .execute()
        )

        rows = result.data or []
        by_author: Dict[str, int] = {}
        total_evidences = 0

        for row in rows:
            author_id = row.get("author_id")
            if author_id:
                evidence_count = int(row.get("evidence_count") or 0)
                by_author[author_id] = evidence_count
                total_evidences += evidence_count

        return True, {
            "total_evidences": total_evidences,
            "evidences_by_author": by_author,
        }, "Resumen de evidencias del caso cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, empty_summary, (
            "No fue posible consultar el resumen de evidencias del caso. "
            f"Detalle tecnico: {exc}"
        )
