from __future__ import annotations

import streamlit as st

try:
    from services.progress_service import upsert_student_progress
    from services.role_service import get_assigned_role_for_user_case
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.progress_service import upsert_student_progress
    from app.services.role_service import get_assigned_role_for_user_case
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Mi rol y preparación inicial",
    page_icon="🎭",
    layout="wide",
)

apply_compact_academic_style()

st.title("Mi rol y preparación inicial")
st.write(
    "Esta pantalla presenta el rol asignado al estudiante y orienta la "
    "fase breve de investigación inicial antes de construir el perfil público del actor."
)

# ---------------------------------------------------------
# Validación básica del flujo
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
guide_completed = st.session_state.get("guide_completed", False)
case_context_completed = st.session_state.get("case_context_completed", False)
validated_user_record = st.session_state.get("validated_user_record", {}) or {}

if not access_validated:
    st.warning(
        "Antes de entrar a esta pantalla, debe completarse el acceso y validación."
    )
    st.stop()

if validated_user_record.get("is_admin") is True:
    st.info(
        "Este usuario tiene perfil administrativo. Para continuar, ingrese al "
        "Panel administrativo."
    )
    st.stop()

if not guide_completed:
    st.warning(
        "Antes de continuar, debe leerse y completarse la Guía inicial del ejercicio."
    )
    st.stop()

if not case_context_completed:
    st.warning(
        "Antes de continuar, debe revisarse el contexto general del caso."
    )
    st.stop()

if "role_assigned" not in st.session_state:
    st.session_state["role_assigned"] = False

if "role_preparation_completed" not in st.session_state:
    st.session_state["role_preparation_completed"] = False

# ---------------------------------------------------------
# Rol asignado desde base de datos
# ---------------------------------------------------------
validated_user_email = st.session_state.get("validated_user_email", "")
case_slug = str(validated_user_record.get("case_slug") or "").strip()

if not validated_user_email or not case_slug:
    st.error(
        "No fue posible identificar el usuario validado y el caso activo para "
        "consultar el rol asignado."
    )
    st.stop()

ok_role, role_context, role_message = get_assigned_role_for_user_case(
    validated_user_email,
    case_slug,
)

if not ok_role or role_context is None:
    st.error(role_message)
    st.stop()

assigned_role = role_context["assigned_role"]
st.session_state["profile_id"] = role_context["profile_id"]
st.session_state["case_id"] = role_context["case_id"]
st.session_state["role_id"] = role_context["role_id"]
st.session_state["assigned_role"] = assigned_role
st.session_state["role_assigned"] = True

st.success("Flujo correcto: acceso validado, guía leída y contexto del caso revisado.")

st.divider()

# ---------------------------------------------------------
# Presentación del rol
# ---------------------------------------------------------
st.header("1. Rol asignado")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(assigned_role["name"])
    st.write(assigned_role["mission"])

with col2:
    st.metric("Tipo de actor", assigned_role["actor_type"])

st.divider()

# ---------------------------------------------------------
# Ficha del rol
# ---------------------------------------------------------
st.header("2. Ficha inicial del actor")

ficha1, ficha2 = st.columns(2)

with ficha1:
    st.subheader("Intereses principales")
    for item in assigned_role["interests"]:
        st.markdown(f"- {item}")

    st.subheader("Restricciones")
    for item in assigned_role["constraints"]:
        st.markdown(f"- {item}")

with ficha2:
    st.subheader("Recursos")
    for item in assigned_role["resources"]:
        st.markdown(f"- {item}")

    st.subheader("Puntos no negociables")
    for item in assigned_role["non_negotiable_points"]:
        st.markdown(f"- {item}")

st.subheader("Criterio de éxito")
st.write(assigned_role["success_criteria"])

st.divider()

# ---------------------------------------------------------
# Orientación para la investigación inicial
# ---------------------------------------------------------
st.header("3. Preparación inicial del rol")

st.write(
    "Antes de construir su perfil público y participar en la discusión, "
    "conviene dedicar un momento breve a investigar cómo este actor se "
    "ubica frente al conflicto."
)

st.markdown(
    """
    **Preguntas orientadoras para su preparación:**
    - ¿qué defiende este actor frente al conflicto?
    - ¿qué intereses no puede abandonar?
    - ¿qué argumentos podría usar con mayor fuerza?
    - ¿qué limitaciones tiene dentro del debate?
    - ¿qué tipo de evidencia podría ayudar a sostener su postura?
    - ¿cómo podría presentarse públicamente ante otros actores?
    """
)

st.info(
    "Esta fase no busca una investigación extensa todavía, sino una preparación "
    "inicial suficiente para que el perfil del actor y las primeras intervenciones "
    "tengan coherencia."
)

st.divider()

# ---------------------------------------------------------
# Recordatorio metodológico
# ---------------------------------------------------------
st.header("4. Recordatorio metodológico")

st.warning(
    "El rol no se elige ni se modifica. Lo que usted construye es la manera "
    "de presentar públicamente al actor y la estrategia con la que lo representará."
)

st.write(
    "Por esa razón, el paso siguiente no es entrar inmediatamente a discutir, "
    "sino construir primero un perfil público del actor con mayor consistencia."
)

st.divider()

# ---------------------------------------------------------
# Confirmación de preparación
# ---------------------------------------------------------
st.header("5. Confirmación de preparación inicial")

st.write(
    "Cuando considere que ya comprendió su rol y tiene una base suficiente "
    "para presentarlo, puede marcar esta fase como completada."
)

if st.button("He revisado mi rol y realicé la preparación inicial"):
    st.session_state["role_preparation_completed"] = True
    ok_progress, _saved_progress, progress_message = upsert_student_progress(
        st.session_state["profile_id"],
        st.session_state["case_id"],
        role_preparation_completed=True,
    )
    if not ok_progress:
        st.warning(progress_message)
    st.success(
        "La preparación inicial del rol quedó marcada como completada. "
        "El siguiente paso recomendado es construir el perfil público del actor."
    )

if st.session_state["role_preparation_completed"]:
    st.info(
        "Estado actual: preparación inicial del rol completada. "
        "Siguiente pantalla sugerida: Perfil público del actor."
    )

st.divider()
st.caption(
    "Nota técnica: esta es una versión funcional inicial. Más adelante, "
    "la ficha del rol deberá cargarse dinámicamente desde la base de datos."
)
