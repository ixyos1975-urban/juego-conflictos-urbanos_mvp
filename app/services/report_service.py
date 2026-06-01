"""Servicios read-only para reportes administrativos del caso."""

from __future__ import annotations

from io import BytesIO
import json
from typing import Any, Dict, List, Tuple

import pandas as pd

try:
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.supabase_client import get_supabase_client


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _rows_to_frame(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    clean_rows = [
        {key: _json_safe(value) for key, value in row.items()}
        for row in rows
    ]
    return pd.DataFrame(clean_rows)


def _write_sheet(writer: pd.ExcelWriter, sheet_name: str, rows: List[Dict[str, Any]]) -> None:
    frame = _rows_to_frame(rows)
    if frame.empty:
        frame = pd.DataFrame([{"estado": "Sin datos disponibles"}])
    frame.to_excel(writer, sheet_name=sheet_name, index=False)


def build_case_report_excel(case_id: str) -> Tuple[bool, bytes, str]:
    """Construye un libro Excel administrativo sin modificar datos."""
    if not case_id or not str(case_id).strip():
        return False, b"", "No se recibio un case_id valido para generar reporte."

    client = get_supabase_client()

    if client is None:
        return False, b"", (
            "No fue posible generar el reporte porque aun no hay credenciales "
            "validas de Supabase."
        )

    clean_case_id = str(case_id).strip()

    try:
        ranking_rows = (
            client.rpc(
                "get_case_ranking_for_case_secure",
                {"p_case_id": clean_case_id},
            )
            .execute()
            .data
            or []
        )

        student_rows = (
            client.rpc(
                "get_students_with_roles_for_case_secure",
                {"p_case_id": clean_case_id},
            )
            .execute()
            .data
            or []
        )

        intervention_rows = (
            client.rpc(
                "get_interventions_for_teacher_review_secure",
                {
                    "p_case_id": clean_case_id,
                    "p_student_profile_id": None,
                },
            )
            .execute()
            .data
            or []
        )

        intervention_ids = [
            row.get("id") or row.get("intervention_id")
            for row in intervention_rows
            if row.get("id") or row.get("intervention_id")
        ]

        intervention_id_set = {str(intervention_id) for intervention_id in intervention_ids}
        teacher_review_rows = []
        evidence_rows = []

        for student in student_rows:
            profile_id = student.get("profile_id") or student.get("user_id")
            if not profile_id:
                continue

            teacher_review_rows.extend(
                client.rpc(
                    "get_teacher_reviews_for_student_secure",
                    {
                        "p_case_id": clean_case_id,
                        "p_profile_id": str(profile_id),
                    },
                )
                .execute()
                .data
                or []
            )

            student_evidences = (
                client.rpc(
                    "get_evidences_for_user_secure",
                    {"p_uploaded_by": str(profile_id)},
                )
                .execute()
                .data
                or []
            )
            evidence_rows.extend([
                evidence
                for evidence in student_evidences
                if str(evidence.get("intervention_id") or "") in intervention_id_set
            ])

        ai_review_rows = (
            client.rpc(
                "get_ai_reviews_for_case_secure",
                {"p_case_id": clean_case_id},
            )
            .execute()
            .data
            or []
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            _write_sheet(writer, "ranking", ranking_rows)
            _write_sheet(writer, "estudiantes", student_rows)
            _write_sheet(writer, "intervenciones", intervention_rows)
            _write_sheet(writer, "revisiones_docentes", teacher_review_rows)
            _write_sheet(writer, "lecturas_ia", ai_review_rows)
            _write_sheet(writer, "evidencias", evidence_rows)

        return True, output.getvalue(), "Reporte Excel generado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, b"", (
            "No fue posible generar el reporte administrativo. "
            f"Detalle tecnico: {exc}"
        )
