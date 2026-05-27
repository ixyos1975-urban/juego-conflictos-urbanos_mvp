"""Servicios minimos para evaluacion docente sobre teacher_reviews."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


RATING_VALUES = ["excelente", "sobresaliente", "bueno", "regular", "pobre"]
REVIEW_STATUS_VALUES = ["pendiente", "validada", "observada"]
DISCUSSION_RESULT_VALUES = ["ganada", "empatada", "perdida", "no_definida"]
ARGUMENT_STRENGTH_VALUES = ["alta", "media", "baja"]
ARGUMENT_TYPE_VALUES = [
    "tecnico",
    "normativo",
    "comunitario",
    "economico",
    "ambiental",
    "politico",
    "mixto",
    "indefinido",
]
MODERATION_STATUS_VALUES = ["normal", "alerta", "revision"]
ROLE_COHERENCE_VALUES = ["alta", "media", "baja"]
RATING_SCORES = {
    "excelente": 5,
    "sobresaliente": 4,
    "bueno": 3,
    "regular": 2,
    "pobre": 1,
}
DISCUSSION_RESULT_SCORES = {
    "ganada": 5,
    "empatada": 3,
    "perdida": 1,
    "no_definida": 0,
}


def _index_by_id(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        row.get("id"): row
        for row in rows
        if row.get("id")
    }


def _first_present(record: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def get_interventions_for_teacher_review(
    case_id: str,
    student_profile_id: Optional[str] = None,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista intervenciones reales disponibles para revision docente."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar intervenciones."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar intervenciones porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_interventions_for_teacher_review_secure",
                {
                    "p_case_id": str(case_id).strip(),
                    "p_student_profile_id": (
                        str(student_profile_id).strip()
                        if student_profile_id
                        else None
                    ),
                },
            )
            .execute()
        )
        interventions = result.data or []

        if not interventions:
            return True, [], "No hay intervenciones disponibles para revisar."

        return True, interventions, "Intervenciones para revision cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar intervenciones para revision en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_teacher_review_for_intervention(
    intervention_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca la revision docente asociada a una intervencion."""
    if not intervention_id or not str(intervention_id).strip():
        return False, None, "No se recibio un intervention_id valido para consultar revision."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar la revision porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_teacher_review_for_intervention_secure",
                {"p_intervention_id": str(intervention_id).strip()},
            )
            .execute()
        )

        rows = result.data or []
        if not rows:
            return True, None, "No existe revision docente para esta intervencion."

        return True, rows[0], "Revision docente encontrada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar la revision docente en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def upsert_teacher_review(
    intervention_id: str,
    reviewed_by: str,
    intervention_rating: str,
    role_coherence_rating: str,
    argument_quality_rating: str,
    evidence_use_rating: str,
    discussion_result: str,
    review_status: str,
    teacher_comment: str = "",
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea o actualiza una revision docente por intervencion."""
    if not intervention_id or not str(intervention_id).strip():
        return False, None, "No se recibio una intervencion valida para revisar."

    if not reviewed_by or not str(reviewed_by).strip():
        return False, None, "No se recibio un perfil docente valido para revisar."

    ratings = [
        intervention_rating,
        role_coherence_rating,
        argument_quality_rating,
        evidence_use_rating,
    ]

    if any(rating not in RATING_VALUES for rating in ratings):
        return False, None, "Una o mas valoraciones docentes no son validas."

    if discussion_result not in DISCUSSION_RESULT_VALUES:
        return False, None, "El resultado de discusion seleccionado no es valido."

    if review_status not in REVIEW_STATUS_VALUES:
        return False, None, "El estado de revision seleccionado no es valido."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible guardar la revision porque aun no hay "
            "credenciales validas de Supabase."
        )

    intervention_rating_score = RATING_SCORES[intervention_rating]
    role_coherence_score = RATING_SCORES[role_coherence_rating]
    argument_quality_score = RATING_SCORES[argument_quality_rating]
    evidence_use_score = RATING_SCORES[evidence_use_rating]
    discussion_result_score = DISCUSSION_RESULT_SCORES[discussion_result]
    final_score = round(
        (
            intervention_rating_score
            + role_coherence_score
            + argument_quality_score
            + evidence_use_score
            + discussion_result_score
        ) / 5,
        2,
    )

    payload = {
        "intervention_id": str(intervention_id).strip(),
        "reviewed_by": str(reviewed_by).strip(),
        "review_status": review_status,
        "intervention_rating": intervention_rating,
        "intervention_rating_score": intervention_rating_score,
        "role_coherence_rating": role_coherence_rating,
        "role_coherence_score": role_coherence_score,
        "argument_quality_rating": argument_quality_rating,
        "argument_quality_score": argument_quality_score,
        "evidence_use_rating": evidence_use_rating,
        "evidence_use_score": evidence_use_score,
        "discussion_result": discussion_result,
        "discussion_result_score": discussion_result_score,
        "final_score": final_score,
        "teacher_comment": str(teacher_comment or "").strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = (
            client.rpc(
                "upsert_teacher_review_secure",
                {
                    "p_intervention_id": payload["intervention_id"],
                    "p_reviewed_by": payload["reviewed_by"],
                    "p_review_status": payload["review_status"],
                    "p_intervention_rating": payload["intervention_rating"],
                    "p_intervention_rating_score": payload[
                        "intervention_rating_score"
                    ],
                    "p_role_coherence_rating": payload["role_coherence_rating"],
                    "p_role_coherence_score": payload["role_coherence_score"],
                    "p_argument_quality_rating": payload["argument_quality_rating"],
                    "p_argument_quality_score": payload["argument_quality_score"],
                    "p_evidence_use_rating": payload["evidence_use_rating"],
                    "p_evidence_use_score": payload["evidence_use_score"],
                    "p_discussion_result": payload["discussion_result"],
                    "p_discussion_result_score": payload["discussion_result_score"],
                    "p_final_score": payload["final_score"],
                    "p_teacher_comment": payload["teacher_comment"],
                },
            )
            .execute()
        )

        rows = result.data or []
        saved_review = rows[0] if rows else payload

        return True, saved_review, "Revision docente guardada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible guardar la revision docente en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_teacher_reviews_for_student(
    case_id: str,
    profile_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista revisiones docentes de intervenciones de un estudiante."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar revisiones."

    if not profile_id or not str(profile_id).strip():
        return False, [], "No se recibio un profile_id valido para consultar revisiones."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar revisiones porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_teacher_reviews_for_student_secure",
                {
                    "p_case_id": str(case_id).strip(),
                    "p_profile_id": str(profile_id).strip(),
                },
            )
            .execute()
        )

        return True, result.data or [], "Revisiones docentes cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar revisiones docentes del estudiante. "
            f"Detalle tecnico: {exc}"
        )


def get_ai_review_for_intervention(
    intervention_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca la lectura preliminar de IA asociada a una intervencion."""
    if not intervention_id or not str(intervention_id).strip():
        return False, None, "No se recibio un intervention_id valido para consultar IA."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar la lectura de IA porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_ai_review_for_intervention_secure",
                {"p_intervention_id": str(intervention_id).strip()},
            )
            .execute()
        )

        rows = result.data or []
        if not rows:
            return True, None, "No existe lectura preliminar de IA para esta intervencion."

        return True, rows[0], "Lectura preliminar de IA encontrada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar la lectura preliminar de IA en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def upsert_ai_review(
    intervention_id: str,
    argument_strength: str,
    argument_type: str,
    moderation_status: str,
    role_coherence: str,
    evidence_detected: Optional[bool] = None,
    preliminary_score: Optional[float] = None,
    teacher_review_recommended: Optional[bool] = None,
    ai_comment: str = "",
    prompt_version: str = "",
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Crea o actualiza una lectura preliminar de IA por intervencion."""
    if not intervention_id or not str(intervention_id).strip():
        return False, None, "No se recibio una intervencion valida para analizar."

    if argument_strength not in ARGUMENT_STRENGTH_VALUES:
        return False, None, "La fuerza argumentativa seleccionada no es valida."

    if argument_type not in ARGUMENT_TYPE_VALUES:
        return False, None, "El tipo de argumento seleccionado no es valido."

    if moderation_status not in MODERATION_STATUS_VALUES:
        return False, None, "El estado de moderacion seleccionado no es valido."

    if role_coherence not in ROLE_COHERENCE_VALUES:
        return False, None, "La coherencia con el rol seleccionada no es valida."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible guardar la lectura de IA porque aun no hay "
            "credenciales validas de Supabase."
        )

    payload = {
        "intervention_id": str(intervention_id).strip(),
        "argument_strength": argument_strength,
        "argument_type": argument_type,
        "moderation_status": moderation_status,
        "role_coherence": role_coherence,
        "evidence_detected": evidence_detected,
        "preliminary_score": preliminary_score,
        "teacher_review_recommended": teacher_review_recommended,
        "ai_comment": str(ai_comment or "").strip(),
        "prompt_version": str(prompt_version or "").strip(),
    }

    try:
        result = (
            client.rpc(
                "upsert_ai_review_secure",
                {
                    "p_intervention_id": payload["intervention_id"],
                    "p_moderation_status": payload["moderation_status"],
                    "p_role_coherence": payload["role_coherence"],
                    "p_argument_strength": payload["argument_strength"],
                    "p_argument_type": payload["argument_type"],
                    "p_evidence_detected": payload["evidence_detected"],
                    "p_preliminary_score": payload["preliminary_score"],
                    "p_teacher_review_recommended": payload[
                        "teacher_review_recommended"
                    ],
                    "p_ai_comment": payload["ai_comment"],
                    "p_prompt_version": payload["prompt_version"],
                },
            )
            .execute()
        )

        rows = result.data or []
        saved_review = rows[0] if rows else payload

        return True, saved_review, "Lectura preliminar de IA guardada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible guardar la lectura preliminar de IA en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_ai_reviews_for_case(
    case_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista lecturas preliminares de IA de intervenciones de un caso."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar lecturas de IA."

    ok_interventions, interventions, interventions_message = (
        get_interventions_for_teacher_review(case_id)
    )

    if not ok_interventions:
        return False, [], interventions_message

    intervention_ids = [
        row.get("id") or row.get("intervention_id")
        for row in interventions
        if row.get("id") or row.get("intervention_id")
    ]

    if not intervention_ids:
        return True, [], "No hay intervenciones disponibles para lecturas de IA."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar lecturas de IA porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        reviews_result = (
            client.rpc(
                "get_ai_reviews_for_case_secure",
                {"p_case_id": str(case_id).strip()},
            )
            .execute()
        )

        reviews_by_intervention = {
            str(review.get("intervention_id")): review
            for review in (reviews_result.data or [])
            if review.get("intervention_id")
        }

        enriched = []
        for intervention in interventions:
            intervention_id = intervention.get("id") or intervention.get("intervention_id")
            if not intervention_id:
                continue

            review = reviews_by_intervention.get(str(intervention_id))
            if review:
                enriched.append({
                    **review,
                    "intervention_id": str(intervention_id),
                    "author_name": intervention.get("author_name", "Estudiante"),
                    "role_name": intervention.get("role_name", "Rol asignado"),
                    "thread_title": intervention.get("thread_title", "Hilo sin titulo"),
                    "intervention_type": intervention.get("intervention_type", ""),
                    "content": intervention.get("content", ""),
                    "created_at": intervention.get("created_at", ""),
                })

        return True, enriched, "Lecturas preliminares de IA cargadas correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar lecturas preliminares de IA en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def _parse_rpc_integer(value: Any) -> int:
    """Normaliza respuestas RPC que pueden venir como numero, dict o lista."""
    if value in (None, ""):
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        return int(value) if value.strip() else 0

    if isinstance(value, list):
        if not value:
            return 0
        return _parse_rpc_integer(value[0])

    if isinstance(value, dict):
        for key in (
            "rows_updated",
            "refreshed_rows",
            "refresh_case_ranking_for_case_secure",
            "refresh_case_ranking_for_case",
            "count",
        ):
            if key in value:
                return _parse_rpc_integer(value.get(key))

        if len(value) == 1:
            return _parse_rpc_integer(next(iter(value.values())))

    return 0


def refresh_case_ranking_for_case(
    case_id: str,
) -> Tuple[bool, int, str]:
    """Consolida case_ranking usando solo revisiones docentes validadas."""
    if not case_id or not str(case_id).strip():
        return False, 0, "No se recibio un case_id valido para consolidar ranking."

    client = get_supabase_client()

    if client is None:
        return False, 0, (
            "No fue posible consolidar ranking porque aun no hay credenciales "
            "validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "refresh_case_ranking_for_case_secure",
                {"p_case_id": str(case_id).strip()},
            )
            .execute()
        )

        refreshed_rows = _parse_rpc_integer(result.data)

        return (
            True,
            refreshed_rows,
            "Ranking del caso consolidado correctamente.",
        )

    except Exception as exc:  # noqa: BLE001
        return False, 0, (
            "No fue posible consolidar case_ranking en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_case_ranking_for_case(
    case_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lee el ranking consolidado actual de un caso."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar ranking."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar ranking porque aun no hay credenciales "
            "validas de Supabase."
        )

    try:
        ranking_result = (
            client.rpc(
                "get_case_ranking_for_case_secure",
                {"p_case_id": str(case_id).strip()},
            )
            .execute()
        )

        ranking_rows = ranking_result.data or []
        if not ranking_rows:
            return True, [], "Aun no hay ranking consolidado para este caso."

        enriched = []
        for index, row in enumerate(ranking_rows, start=1):
            student_name = (
                row.get("student_name")
                or row.get("full_name")
                or row.get("email")
                or "Estudiante"
            )
            role_name = row.get("role_name") or "Rol no registrado"
            enriched.append({
                **row,
                "position": row.get("position") or index,
                "student_name": student_name,
                "full_name": row.get("full_name") or student_name,
                "email": row.get("email") or "",
                "role_name": role_name,
            })

        return True, enriched, "Ranking consolidado cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar case_ranking en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_case_ranking_for_student(
    case_id: str,
    profile_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Lee la fila consolidada de case_ranking para un estudiante y caso."""
    if not case_id or not str(case_id).strip():
        return False, None, "No se recibio un case_id valido para consultar ranking."

    if not profile_id or not str(profile_id).strip():
        return False, None, "No se recibio un profile_id valido para consultar ranking."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar ranking porque aun no hay credenciales "
            "validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_case_ranking_for_student_secure",
                {
                    "p_case_id": str(case_id).strip(),
                    "p_user_id": str(profile_id).strip(),
                },
            )
            .execute()
        )

        rows = result.data or []
        if not rows:
            return True, None, "Aun no hay ranking consolidado para este estudiante."

        return True, rows[0], "Ranking consolidado del estudiante cargado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar case_ranking del estudiante en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def build_review_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Entrega un resumen simple sin convertir todavia a nota numerica."""
    return {
        "total_reviews": len(reviews),
        "validated_reviews": sum(
            1 for review in reviews if review.get("review_status") == "validada"
        ),
        "observed_reviews": sum(
            1 for review in reviews if review.get("review_status") == "observada"
        ),
        "pending_reviews": sum(
            1 for review in reviews if review.get("review_status") == "pendiente"
        ),
    }
