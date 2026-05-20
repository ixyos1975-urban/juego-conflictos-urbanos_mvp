"""Parser y validador de respuestas AI para ai_reviews."""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple


ARGUMENT_STRENGTH_VALUES = {"alta", "media", "baja"}
ARGUMENT_TYPE_VALUES = {
    "tecnico",
    "normativo",
    "comunitario",
    "economico",
    "ambiental",
    "politico",
    "mixto",
    "indefinido",
}
ARGUMENT_TYPE_ALIASES = {
    "tecnica": "tecnico",
    "técnico": "tecnico",
    "técnica": "tecnico",
    "urbanistico": "tecnico",
    "urbanística": "tecnico",
    "urbanistica": "tecnico",
    "espacial": "tecnico",
    "legal": "normativo",
    "juridico": "normativo",
    "jurídico": "normativo",
    "regulatorio": "normativo",
    "regulatoria": "normativo",
    "social": "comunitario",
    "barrial": "comunitario",
    "ciudadano": "comunitario",
    "ciudadana": "comunitario",
    "vecinal": "comunitario",
}
MODERATION_STATUS_VALUES = {"normal", "alerta", "revision"}
ROLE_COHERENCE_VALUES = {"alta", "media", "baja"}


def _extract_json(text: str) -> Dict[str, Any]:
    clean_text = str(text or "").strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`").strip()
        if clean_text.lower().startswith("json"):
            clean_text = clean_text[4:].strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(clean_text[start : end + 1])


def _normalize_catalog(value: Any, allowed: set[str], default: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in allowed else default


def _normalize_argument_type(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in ARGUMENT_TYPE_VALUES:
        return candidate
    return ARGUMENT_TYPE_ALIASES.get(candidate, "indefinido")


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    candidate = str(value or "").strip().lower()
    return candidate in {"true", "1", "yes", "si", "on"}


def parse_ai_review_response(
    raw_response: str,
    prompt_version: str,
) -> Tuple[bool, Dict[str, Any] | None, str]:
    """Devuelve una estructura validada para precargar/guardar ai_reviews."""
    try:
        payload = _extract_json(raw_response)
    except Exception:  # noqa: BLE001
        return False, None, "La respuesta AI no tiene un JSON valido."

    try:
        preliminary_score = float(payload.get("preliminary_score", 0))
    except (TypeError, ValueError):
        preliminary_score = 0.0

    preliminary_score = max(0.0, min(5.0, preliminary_score))
    evidence_detected = _normalize_bool(payload.get("evidence_detected", False))
    argument_strength = _normalize_catalog(
        payload.get("argument_strength"),
        ARGUMENT_STRENGTH_VALUES,
        "media",
    )

    if not evidence_detected and argument_strength == "alta":
        argument_strength = "media"

    if not evidence_detected and preliminary_score > 3.5:
        preliminary_score = 3.5

    parsed = {
        "argument_strength": argument_strength,
        "argument_type": _normalize_argument_type(payload.get("argument_type")),
        "moderation_status": _normalize_catalog(
            payload.get("moderation_status"),
            MODERATION_STATUS_VALUES,
            "normal",
        ),
        "role_coherence": _normalize_catalog(
            payload.get("role_coherence"),
            ROLE_COHERENCE_VALUES,
            "media",
        ),
        "evidence_detected": evidence_detected,
        "preliminary_score": round(preliminary_score, 2),
        "teacher_review_recommended": _normalize_bool(
            payload.get("teacher_review_recommended", False)
        ),
        "ai_comment": str(payload.get("ai_comment") or "").strip(),
        "prompt_version": str(payload.get("prompt_version") or prompt_version).strip(),
    }

    return True, parsed, "Respuesta AI validada correctamente."
