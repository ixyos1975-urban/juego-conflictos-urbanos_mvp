from __future__ import annotations

import streamlit as st

try:
    from services.evidence_service import (
        create_evidence,
        get_evidences_for_user,
        get_interventions_available_for_evidence,
    )
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.evidence_service import (
        create_evidence,
        get_evidences_for_user,
        get_interventions_available_for_evidence,
    )
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Evidencias",
    page_icon="📎",
    layout="wide",
)

apply_compact_academic_style()

st.title("Evidencias")
st.write(
    "Esta pantalla permite registrar y consultar soportes del ejercicio. "
    "Su función es ayudar a que las intervenciones no dependan solo de opiniones, "
    "sino que puedan sostenerse con referencias, documentos o enlaces pertinentes."
)

# ---------------------------------------------------------
# Validación del flujo previo
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
validated_user = st.session_state.get("validated_user_record", {}) or {}
guide_completed = st.session_state.get("guide_completed", False)
case_context_completed = st.session_state.get("case_context_completed", False)
role_preparation_completed = st.session_state.get("role_preparation_completed", False)
public_actor_profile_completed = st.session_state.get("public_actor_profile_completed", False)

if not access_validated:
    st.warning("Antes de entrar a Evidencias, debe completarse el acceso y validación.")
    st.stop()

if validated_user.get("is_admin") is True:
    st.info(
        "Este usuario tiene perfil administrativo. Para continuar, ingrese al "
        "Panel administrativo."
    )
    st.stop()

missing_onboarding_steps = []
if not guide_completed:
    missing_onboarding_steps.append("Guía inicial del ejercicio")
if not case_context_completed:
    missing_onboarding_steps.append("Contexto del caso")
if not role_preparation_completed:
    missing_onboarding_steps.append("Mi rol y preparación")
if not public_actor_profile_completed:
    missing_onboarding_steps.append("Perfil público del actor")

if missing_onboarding_steps:
    st.warning(
        "Antes de entrar a Evidencias, falta completar: "
        + ", ".join(missing_onboarding_steps)
        + "."
    )
    st.stop()

case_id = st.session_state.get("case_id", "")
profile_id = st.session_state.get("profile_id", "")
role_id = st.session_state.get("role_id", "")

if not case_id or not profile_id or not role_id:
    st.error(
        "No fue posible identificar el caso, el usuario y el rol activo para "
        "cargar evidencias."
    )
    st.stop()

ok_interventions, posts, posts_message = get_interventions_available_for_evidence(
    case_id,
    profile_id,
    role_id,
)

if not ok_interventions:
    st.error(posts_message)
    posts = []

ok_evidences, evidences, evidences_message = get_evidences_for_user(profile_id)

if not ok_evidences:
    st.error(evidences_message)
    evidences = []

# ---------------------------------------------------------
# Resumen inicial
# ---------------------------------------------------------
st.divider()
st.header("1. Estado general de evidencias")

total_evidences = len(evidences)
col1, col2 = st.columns(2)

with col1:
    st.metric("Evidencias registradas", total_evidences)

with col2:
    st.metric("Intervenciones disponibles para enlazar", len(posts))

st.info(
    "En esta versión funcional inicial, las evidencias se guardan de manera temporal "
    "en session_state. Más adelante se conectarán a la base de datos."
)

# ---------------------------------------------------------
# Registro de una nueva evidencia
# ---------------------------------------------------------
st.divider()
st.header("2. Registrar nueva evidencia")

possible_posts = {}
for post in posts:
    content_fragment = (post.get("content") or post.get("title") or "").strip()
    if len(content_fragment) > 70:
        content_fragment = content_fragment[:67].rstrip() + "..."

    label = (
        f"Hilo: {post.get('thread_title') or 'Hilo sin título'} | "
        f"{post['intervention_type']} — {content_fragment or 'Intervención sin texto'}"
    )
    possible_posts[label] = post["id"]

if not possible_posts:
    st.warning(
        "Todavía no hay intervenciones disponibles para asociar evidencias. "
        "Primero publique una intervención en la sala de discusión."
    )
else:
    evidence_type_options = {
        "Técnica": "tecnica",
        "Normativa": "normativa",
        "Documento oficial": "documento_oficial",
        "Académica": "academica",
        "Cartográfica": "cartografica",
        "Nota de prensa": "investigacion_autonoma",
    }

    with st.form("evidence_form"):
        evidence_type_label = st.selectbox(
            "Tipo de evidencia",
            options=list(evidence_type_options.keys()),
        )

        title = st.text_input(
            "Título breve de la evidencia",
            placeholder="Ejemplo: Artículo sobre permanencia barrial",
        )

        description = st.text_area(
            "Descripción breve",
            height=100,
            placeholder="Explique de manera breve por qué esta evidencia es relevante.",
        )

        reference_text = st.text_area(
            "Referencia o cita breve",
            height=100,
            placeholder="Puede copiar una referencia, cita corta o dato clave.",
        )

        external_url = st.text_input(
            "Enlace externo (opcional)",
            placeholder="https://...",
        )

        linked_post_label = st.selectbox(
            "Intervención asociada (opcional)",
            options=list(possible_posts.keys()),
        )

        submitted = st.form_submit_button("Guardar evidencia")

    if submitted:
        clean_title = title.strip()
        clean_description = description.strip()
        clean_reference = reference_text.strip()
        clean_url = external_url.strip()
        linked_post_id = possible_posts[linked_post_label]
        evidence_type = evidence_type_options[evidence_type_label]

        if not clean_title:
            st.error("Debe ingresar al menos un título breve para la evidencia.")
        elif not clean_description and not clean_reference and not clean_url:
            st.error(
                "Debe completar al menos uno de estos campos: descripción, referencia o enlace externo."
            )
        else:
            ok_create, _created_evidence, create_message = create_evidence(
                intervention_id=linked_post_id,
                uploaded_by=profile_id,
                evidence_type=evidence_type,
                title=clean_title,
                description=clean_description,
                reference_text=clean_reference,
                external_url=clean_url,
            )

            if ok_create:
                st.success(
                    "La evidencia fue registrada correctamente en esta versión funcional inicial."
                )
            else:
                st.error(create_message)

# ---------------------------------------------------------
# Listado de evidencias
# ---------------------------------------------------------
st.divider()
st.header("3. Evidencias registradas")

if not evidences:
    st.warning("Todavía no hay evidencias registradas.")
else:
    for evidence in evidences:
        with st.container(border=True):
            top1, top2 = st.columns([2, 1])

            with top1:
                st.write(f"**{evidence['title']}**")
                st.caption(f"Tipo: {evidence['evidence_type']}")

            with top2:
                st.caption(evidence["created_at"])

            if evidence["description"]:
                st.write(evidence["description"])

            if evidence["reference_text"]:
                st.markdown("**Referencia o cita breve:**")
                st.write(evidence["reference_text"])

            if evidence["external_url"]:
                st.markdown("**Enlace externo:**")
                st.write(evidence["external_url"])

            if evidence["intervention_id"]:
                st.caption(f"Asociada a la intervención: {evidence['intervention_id']}")
            else:
                st.caption("Sin intervención asociada todavía")

# ---------------------------------------------------------
# Recomendaciones
# ---------------------------------------------------------
st.divider()
st.header("4. Recomendaciones de uso")

st.markdown(
    """
    - use evidencias que realmente ayuden a sostener su postura;  
    - procure que sean pertinentes para el conflicto y para el rol;  
    - no registre enlaces sin explicación;  
    - si una evidencia respalda una intervención, conviene asociarla;  
    - recuerde que la calidad del sustento también será leída en la evaluación.
    """
)

st.caption(
    "Nota técnica: en una etapa posterior, esta pantalla permitirá cargar evidencias "
    "reales desde base de datos y enlazarlas directamente a intervenciones existentes."
)
