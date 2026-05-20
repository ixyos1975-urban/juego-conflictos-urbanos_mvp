"""Construccion de prompts para lecturas preliminares AI."""

from __future__ import annotations

from typing import Any, Dict


def build_ai_review_prompt(
    intervention: Dict[str, Any],
    case_record: Dict[str, Any],
    prompt_version: str,
) -> str:
    """Arma un prompt acotado y pide salida JSON estricta."""
    return f"""
Genera una lectura preliminar de apoyo docente para una intervencion en un juego
de roles urbano. No emitas nota final, ranking ni evaluacion definitiva.

Version del prompt: {prompt_version}

Caso:
- titulo: {case_record.get("title") or case_record.get("slug") or "Caso activo"}
- fase: {case_record.get("phase") or "No definida"}
- estado: {case_record.get("status") or "No definido"}

Intervencion:
- id: {intervention.get("id") or intervention.get("intervention_id") or "No disponible"}
- hilo: {intervention.get("thread_title") or "Hilo no disponible"}
- rol: {intervention.get("role_name") or "Rol asignado"}
- autor: {intervention.get("author_name") or intervention.get("author_email") or "No disponible"}
- tipo: {intervention.get("intervention_type") or "intervencion"}
- contenido: {intervention.get("content") or intervention.get("title") or ""}

Devuelve exclusivamente un JSON valido con estas llaves:
{{
  "argument_strength": "alta|media|baja",
  "argument_type": "tecnico|normativo|comunitario|economico|ambiental|politico|mixto|indefinido",
  "moderation_status": "normal|alerta|revision",
  "role_coherence": "alta|media|baja",
  "evidence_detected": true,
  "preliminary_score": 0.0,
  "teacher_review_recommended": true,
  "ai_comment": "comentario breve para el docente",
  "prompt_version": "{prompt_version}"
}}

Reglas:
- Usa solo los valores permitidos en cada campo.
- preliminary_score debe estar entre 0 y 5.
- Evalua con criterio exigente de pregrado: no confundas buena redaccion o
  postura clara con argumentacion solida.
- evidence_detected solo debe ser true si el texto incluye evidencia explicita
  y reconocible: dato verificable, norma o instrumento citado, autor o fuente
  mencionada, caso comparado claramente identificado o referencia documental
  concreta.
- No marques evidence_detected cuando solo haya afirmaciones generales,
  hipotesis, impresiones, lugares comunes o alusiones vagas sin fuente concreta.
- argument_strength puede ser alta solo si aparecen simultaneamente postura
  clara, justificacion desarrollada, soporte explicito y coherencia interna
  suficiente.
- Si falta soporte explicito, aunque el texto este bien redactado, la fuerza
  argumentativa debe tender a media, no alta.
- Clasifica argument_type por la dimension principal del argumento, no por
  palabras sueltas o menciones secundarias.
- Usa comunitario cuando el nucleo este en permanencia barrial, afectacion
  social, desplazamiento, participacion, redes comunitarias, vida cotidiana o
  justicia espacial. No uses mixto solo porque aparezcan terminos urbanos
  secundarios.
- Usa tecnico cuando predominen compatibilidad urbanistica, implantacion,
  cargas, mitigacion, movilidad, servicios, impacto fisico-espacial o
  instrumentos tecnicos de soporte. No lo conviertas en normativo si no hay
  referencia normativa explicita.
- Usa normativo cuando el argumento se apoye principalmente en una norma,
  instrumento, obligacion regulatoria, POT, tratamiento, cumplimiento formal,
  articulo, acuerdo o marco legal explicito. No marques normativo solo por una
  alusion general a "cumplimiento".
- Usa mixto solo cuando haya equilibrio real entre dos o mas dimensiones
  argumentativas. Evita mixto como salida por defecto: si hay enfasis claro en
  una dimension, prioriza esa categoria.
- Una intervencion con postura clara y justificacion general, pero sin soporte
  explicito, debe quedar normalmente cerca de 3.0 a 3.5, no en 4.0 o mas.
- role_coherence debe ser alta solo si la postura, el vocabulario y la
  preocupacion central coinciden claramente con el actor asignado.
- ai_comment debe ser breve, prudente y no conclusivo; debe indicar una
  fortaleza concreta, que falta para subir de nivel argumentativo y por que se
  clasifico ese tipo de argumento.
- No incluyas markdown ni texto fuera del JSON.
""".strip()
