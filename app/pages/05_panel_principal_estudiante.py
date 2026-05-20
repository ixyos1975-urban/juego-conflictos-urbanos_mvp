from __future__ import annotations

import streamlit as st

try:
    from services.case_service import get_case_by_slug
    from services.discussion_service import get_student_participation_summary
    from services.evidence_service import get_evidences_for_user
    from services.profile_service import get_profile_for_user_case, normalize_profile_data
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.case_service import get_case_by_slug
    from app.services.discussion_service import get_student_participation_summary
    from app.services.evidence_service import get_evidences_for_user
    from app.services.profile_service import get_profile_for_user_case, normalize_profile_data
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Panel principal del estudiante",
    page_icon="🏠",
    layout="wide",
)

apply_compact_academic_style()

st.title("Panel principal del estudiante")
st.write(
    "Este es el entorno recurrente de entrada del estudiante. "
    "Desde aquí podrá revisar su estado general dentro del ejercicio "
    "y acceder a las principales áreas de trabajo."
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
    st.warning("Antes de entrar al panel principal, debe completarse el acceso y validación.")
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
        "Antes de entrar al panel principal, falta completar: "
        + ", ".join(missing_onboarding_steps)
        + "."
    )
    st.stop()

# ---------------------------------------------------------
# Datos base reales disponibles
# ---------------------------------------------------------
validated_user_email = st.session_state.get("validated_user_email", "")
case_slug = str(validated_user.get("case_slug") or "").strip()
case_id = st.session_state.get("case_id", "")
profile_id = st.session_state.get("profile_id", "")
role_id = st.session_state.get("role_id", "")
assigned_role = st.session_state.get("assigned_role", {}) or {}
case_record = st.session_state.get("case_record", {}) or {}

if not validated_user_email or not case_slug or not case_id or not profile_id or not role_id:
    st.error(
        "No fue posible identificar el usuario, el caso y el rol activo para "
        "cargar el panel principal."
    )
    st.stop()

profile = st.session_state.get("public_actor_profile", {}) or {}
if not case_record:
    ok_case, saved_case, case_message = get_case_by_slug(case_slug)
    if ok_case and saved_case:
        case_record = saved_case
        st.session_state["case_record"] = case_record
    elif not ok_case:
        st.warning(case_message)

ok_profile, saved_profile, profile_message = get_profile_for_user_case(
    validated_user_email,
    case_slug,
)

if ok_profile and saved_profile:
    profile = normalize_profile_data(saved_profile)
    st.session_state["public_actor_profile"] = profile
elif not ok_profile:
    st.warning(profile_message)

ok_participation, participation_summary, participation_message = (
    get_student_participation_summary(case_id, profile_id, role_id)
)

if not ok_participation:
    st.warning(participation_message)

ok_evidences, evidences, evidences_message = get_evidences_for_user(profile_id)

if not ok_evidences:
    st.warning(evidences_message)
    evidences = []

participation_summary = {
    "interventions": participation_summary.get("interventions", 0),
    "responses": participation_summary.get("responses", 0),
    "evidences": len(evidences),
    "threads_used": participation_summary.get("threads_used", 0),
}

current_case = {
    "title": case_record.get("title") or validated_user.get("case_slug", "Caso activo"),
    "phase": case_record.get("phase") or "Apertura",
    "status": case_record.get("status") or "Activo",
    "group_name": validated_user.get("group_name", "Grupo no definido"),
}

provisional_results = {
    "ranking_position": "No disponible aún",
    "role_score": "Pendiente",
    "argumentation_score": "Pendiente",
    "evidence_score": "Pendiente",
    "interaction_score": "Pendiente",
    "strategy_score": "Pendiente",
}

st.success("Flujo correcto: el estudiante ya completó la fase de entrada al sistema.")

# ---------------------------------------------------------
# Encabezado del panel
# ---------------------------------------------------------
st.divider()
col1, col2 = st.columns([2, 1])

with col1:
    st.header(f"Bienvenido, {validated_user.get('full_name', 'Estudiante')}")
    st.write(f"**Caso activo:** {current_case['title']}")
    st.write(f"**Grupo:** {current_case['group_name']}")
    st.write(f"**Fase actual del ejercicio:** {current_case['phase']}")

with col2:
    st.metric("Estado del caso", current_case["status"])
    st.metric("Rol visible", profile.get("display_name") or assigned_role.get("name") or "Sin perfil definido")

# ---------------------------------------------------------
# Resumen del actor
# ---------------------------------------------------------
st.divider()
st.header("1. Estado general del actor")

actor_col1, actor_col2 = st.columns(2)

with actor_col1:
    st.subheader("Identidad pública")
    st.write(profile.get("display_name") or "Sin definir")
    st.caption("Esta es la forma en que el actor se presenta ante la comunidad del juego.")

    st.subheader("Postura inicial")
    st.write(profile.get("initial_position") or "Sin definir")

with actor_col2:
    st.subheader("Interés principal")
    st.write(profile.get("main_interest") or "Sin definir")

    st.subheader("Punto no negociable")
    st.write(profile.get("non_negotiable_point") or "Sin definir")

# ---------------------------------------------------------
# Resumen de participación
# ---------------------------------------------------------
st.divider()
st.header("2. Resumen de participación")

p1, p2, p3, p4 = st.columns(4)

with p1:
    st.metric("Intervenciones", participation_summary["interventions"])

with p2:
    st.metric("Respuestas", participation_summary["responses"])

with p3:
    st.metric("Evidencias", participation_summary["evidences"])

with p4:
    st.metric("Hilos usados", participation_summary["threads_used"])

st.info(
    "Estos valores se calculan a partir de las intervenciones y evidencias "
    "registradas en la base de datos."
)

# ---------------------------------------------------------
# Accesos principales
# ---------------------------------------------------------
st.divider()
st.header("3. Accesos principales del ejercicio")

nav1, nav2, nav3, nav4 = st.columns(4)

with nav1:
    if st.button("Ir a discusión", use_container_width=True):
        st.switch_page("pages/06_sala_de_discusion.py")

with nav2:
    if st.button("Ir a evidencias", use_container_width=True):
        st.switch_page("pages/07_evidencias.py")

with nav3:
    if st.button("Ver resultados", use_container_width=True):
        st.switch_page("pages/08_resultados_estudiante.py")

with nav4:
    if st.button("Volver a la guía inicial", use_container_width=True):
        st.switch_page("pages/01_guia_inicial_del_ejercicio.py")

st.caption(
    "Estos accesos llevan a las pantallas principales del flujo estudiante."
)

# ---------------------------------------------------------
# Resumen evaluativo provisional
# ---------------------------------------------------------
st.divider()
st.header("4. Estado evaluativo provisional")

eval_col1, eval_col2 = st.columns(2)

with eval_col1:
    st.write("**Posición en ranking:**")
    st.write(provisional_results["ranking_position"])

    st.write("**Coherencia con el rol:**")
    st.write(provisional_results["role_score"])

    st.write("**Calidad argumentativa:**")
    st.write(provisional_results["argumentation_score"])

with eval_col2:
    st.write("**Uso de evidencia:**")
    st.write(provisional_results["evidence_score"])

    st.write("**Interacción y debate:**")
    st.write(provisional_results["interaction_score"])

    st.write("**Desarrollo estratégico:**")
    st.write(provisional_results["strategy_score"])

st.warning(
    "Los resultados visibles aquí son solo una estructura inicial del panel. "
    "La carga automática de resultados y barras de desempeño se integrará en una etapa posterior."
)

# ---------------------------------------------------------
# Prototipo simple del análisis relacional
# ---------------------------------------------------------
st.divider()
st.header("5. Lectura relacional del ejercicio")

st.write(
    "Aquí podrá mostrarse, en una fase posterior, un prototipo simple del análisis "
    "relacional del juego. En esta primera versión del panel solo se deja reservado "
    "el espacio para esa futura visualización."
)

st.markdown(
    """
    **Más adelante, este bloque podrá mostrar:**
    - posición general dentro de la red de interacciones  
    - intensidad básica de participación  
    - nivel de conexión con otros actores  
    - prototipo simple del análisis de grafos
    """
)

st.caption(
    "La visualización dinámica completa del grafo está prevista para una etapa posterior."
)

# ---------------------------------------------------------
# Orientación de continuidad
# ---------------------------------------------------------
st.divider()
st.header("6. Qué hacer ahora")

st.markdown(
    """
    **Ruta sugerida para el estudiante en esta fase:**
    1. revisar el estado general de su actor;  
    2. entrar a la sala de discusión;  
    3. publicar sus primeras intervenciones;  
    4. registrar evidencias cuando sea necesario;  
    5. volver al panel para seguir su proceso.
    """
)

st.divider()
st.caption(
    "Nota técnica: esta pantalla es una versión funcional inicial del panel principal. "
    "Más adelante integrará navegación real, datos de base de datos, resultados automáticos "
    "y componentes visuales adicionales."
)
