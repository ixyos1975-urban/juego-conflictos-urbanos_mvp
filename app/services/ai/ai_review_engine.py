"""Orquestador de lecturas preliminares AI."""

from __future__ import annotations

from typing import Any, Dict, Tuple

try:
    from config import settings
    from services.ai.deepseek_provider import DeepSeekProvider
    from services.ai.prompt_builder import build_ai_review_prompt
    from services.ai.response_parser import parse_ai_review_response
    from services.ai.provider_base import AIProvider
except ModuleNotFoundError:
    from app.config import settings
    from app.services.ai.deepseek_provider import DeepSeekProvider
    from app.services.ai.prompt_builder import build_ai_review_prompt
    from app.services.ai.response_parser import parse_ai_review_response
    from app.services.ai.provider_base import AIProvider


def get_ai_provider() -> AIProvider:
    """Selecciona proveedor sin acoplar el panel admin al backend."""
    provider_name = (settings.ai_provider or "").strip().lower()

    if provider_name == "deepseek":
        return DeepSeekProvider()

    raise RuntimeError(f"Proveedor AI no soportado: {settings.ai_provider}")


def generate_ai_review_for_intervention(
    intervention: Dict[str, Any],
    case_record: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any] | None, str]:
    """Genera y valida una lectura preliminar, sin guardar en Supabase."""
    if not settings.ai_enabled:
        return False, None, "La generacion AI esta desactivada por configuracion."

    intervention_id = (
        intervention.get("id")
        or intervention.get("intervention_id")
    )

    if not intervention or not intervention_id:
        return False, None, "No se recibio una intervencion valida para analizar."

    try:
        normalized_intervention = {
            **intervention,
            "id": str(intervention_id),
            "intervention_id": str(intervention_id),
        }
        prompt = build_ai_review_prompt(
            normalized_intervention,
            case_record,
            settings.ai_prompt_version,
        )
        raw_response = get_ai_provider().generate(prompt)
        return parse_ai_review_response(raw_response, settings.ai_prompt_version)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"No fue posible generar la lectura AI: {exc}"
