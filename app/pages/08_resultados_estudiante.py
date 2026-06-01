from __future__ import annotations

import streamlit as st

try:
    from services.case_service import get_case_by_slug, is_case_status_closed
    from services.discussion_service import get_student_participation_summary
    from services.evidence_service import get_evidences_for_user
    from services.profile_service import get_profile_for_user_case, normalize_profile_data
    from services.review_service import (
        get_case_ranking_for_student,
        get_teacher_reviews_for_student,
    )
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.case_service import get_case_by_slug, is_case_status_closed
    from app.services.discussion_service import get_student_participation_summary
    from app.services.evidence_service import get_evidences_for_user
    from app.services.profile_service import get_profile_for_user_case, normalize_profile_data
    from app.services.review_service import (
        get_case_ranking_for_student,
        get_teacher_reviews_for_student,
    )
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Resultados del estudiante",
    page_icon="📊",
    layout="wide",
)

apply_compact_academic_style()

st.title("Resultados del estudiante")
st.write(
    "Esta pantalla muestra una lectura clara y pedagógica del desempeño del estudiante "
    "dentro del ejercicio. Aquí se presentan resultados por componente, nota global "
    "y una interpretación breve del proceso."
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
    st.warning("Antes de entrar a Resultados, debe completarse el acceso y validación.")
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
        "Antes de entrar a Resultados, falta completar: "
        + ", ".join(missing_onboarding_steps)
        + "."
    )
    st.stop()

# ---------------------------------------------------------
# Datos reales disponibles
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
        "cargar los resultados."
    )
    st.stop()

if not case_record:
    ok_case, saved_case, case_message = get_case_by_slug(case_slug)
    if ok_case and saved_case:
        case_record = saved_case
        st.session_state["case_record"] = case_record
    elif not ok_case:
        st.warning(case_message)

profile = st.session_state.get("public_actor_profile", {}) or {}
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

ok_reviews, teacher_reviews, reviews_message = get_teacher_reviews_for_student(
    case_id,
    profile_id,
)

if not ok_reviews:
    st.warning(reviews_message)
    teacher_reviews = []

ok_ranking, case_ranking_record, ranking_message = get_case_ranking_for_student(
    case_id,
    profile_id,
)

if not ok_ranking:
    st.warning(ranking_message)
    case_ranking_record = None

rating_labels = {
    "excelente": "Excelente",
    "sobresaliente": "Sobresaliente",
    "bueno": "Bueno",
    "regular": "Regular",
    "pobre": "Pobre",
}
review_status_labels = {
    "pendiente": "Pendiente",
    "validada": "Validada",
    "observada": "Observada",
}
discussion_result_labels = {
    "ganada": "Ganada",
    "empatada": "Empatada",
    "perdida": "Perdida",
    "no_definida": "No definida",
}


def _average_score(rows: list[dict], score_key: str) -> float | None:
    scores = [
        float(row[score_key])
        for row in rows
        if row.get(score_key) is not None
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def _component_label(rows: list[dict], rating_key: str) -> str:
    ratings = [
        str(row.get(rating_key))
        for row in rows
        if row.get(rating_key)
    ]
    if not ratings:
        return "Pendiente de evaluación"

    latest_rating = ratings[0]
    return rating_labels.get(latest_rating, latest_rating)


def _progress_from_score(score: float | None) -> int:
    if score is None:
        return 0
    return int(round((score / 5) * 100))


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


reviews_with_score = [
    review
    for review in teacher_reviews
    if review.get("final_score") is not None
]
average_review_score = _average_score(reviews_with_score, "final_score")
latest_review = teacher_reviews[0] if teacher_reviews else {}
review_status = review_status_labels.get(
    latest_review.get("review_status", ""),
    "Sin revisión docente",
)
review_count = len(teacher_reviews)

current_case = {
    "title": case_record.get("title") or validated_user.get("case_slug", "Caso activo"),
    "phase": case_record.get("phase") or "Apertura",
    "status": case_record.get("status") or "Activo",
}
case_is_closed = is_case_status_closed(case_record)

if not case_is_closed:
    st.warning("Resultado aún no disponible.")
    st.info(
        "Los resultados individuales se habilitan cuando el caso está cerrado "
        "y el panel administrativo consolida el ranking."
    )
    st.stop()

if not case_ranking_record:
    st.warning("Resultado aún no disponible.")
    st.info(
        "El resultado individual aparecerá cuando el panel administrativo "
        "consolide el ranking del caso."
    )
    st.stop()

result_is_provisional = (
    case_ranking_record.get("is_provisional") is True
    or int(case_ranking_record.get("pending_reviews_count") or 0) > 0
    or int(case_ranking_record.get("in_process_reviews_count") or 0) > 0
)

result_components = [
    {
        "name": "Coherencia con el rol",
        "score": _average_score(teacher_reviews, "role_coherence_score"),
        "label": _component_label(teacher_reviews, "role_coherence_rating"),
        "weight": "20%",
        "progress": _progress_from_score(
            _average_score(teacher_reviews, "role_coherence_score")
        ),
    },
    {
        "name": "Calidad argumentativa",
        "score": _average_score(teacher_reviews, "argument_quality_score"),
        "label": _component_label(teacher_reviews, "argument_quality_rating"),
        "weight": "25%",
        "progress": _progress_from_score(
            _average_score(teacher_reviews, "argument_quality_score")
        ),
    },
    {
        "name": "Uso de evidencia y sustento",
        "score": _average_score(teacher_reviews, "evidence_use_score"),
        "label": _component_label(teacher_reviews, "evidence_use_rating"),
        "weight": "20%",
        "progress": _progress_from_score(
            _average_score(teacher_reviews, "evidence_use_score")
        ),
    },
    {
        "name": "Interacción y capacidad de debate",
        "score": _average_score(teacher_reviews, "discussion_result_score"),
        "label": discussion_result_labels.get(
            latest_review.get("discussion_result", ""),
            "Pendiente de evaluación",
        ),
        "weight": "20%",
        "progress": _progress_from_score(
            _average_score(teacher_reviews, "discussion_result_score")
        ),
    },
    {
        "name": "Desarrollo estratégico del proceso y cierre",
        "score": None,
        "label": "Pendiente de evaluación",
        "weight": "15%",
        "progress": 0,
    },
]

final_grade = None
if case_ranking_record and case_ranking_record.get("total_score") is not None:
    final_grade = _to_float(case_ranking_record.get("total_score"))

final_grade_label = (
    f"{final_grade:.2f}/5"
    if final_grade is not None
    else "No disponible"
)

if final_grade is not None:
    global_label = f"Consolidado final: {final_grade:.2f}/5"
elif average_review_score is not None:
    global_label = f"Revisión docente: {average_review_score:.2f}/5"
else:
    global_label = "Pendiente de evaluación"

ranking_position = (
    f"#{case_ranking_record.get('position')}"
    if case_ranking_record and case_ranking_record.get("position") is not None
    else "No disponible todavía"
)
review_comments = [
    str(review.get("teacher_comment", "")).strip()
    for review in teacher_reviews
    if str(review.get("teacher_comment", "")).strip()
]
final_feedback = (
    review_comments[0]
    if review_comments
    else (
        "La retroalimentación evaluativa final todavía no está disponible. "
        "Cuando existan comentarios docentes guardados, aquí aparecerá "
        "una lectura cualitativa del proceso."
    )
)

if result_is_provisional:
    st.warning(
        "Resultado provisional: el caso aún puede tener revisiones pendientes, "
        "en proceso o no estar cerrado formalmente."
    )
else:
    st.success(
        "Resultado final disponible: el caso está cerrado y el ranking individual "
        "ya fue consolidado."
    )

# ---------------------------------------------------------
# Encabezado general
# ---------------------------------------------------------
st.divider()
head1, head2 = st.columns([2, 1])

with head1:
    st.header(f"Resultados de {validated_user.get('full_name', 'Estudiante')}")
    st.markdown(
        f"**Actor visible:** {profile.get('display_name') or 'Sin definir'} · "
        f"**Rol real:** {assigned_role.get('name') or 'Rol asignado'} · "
        f"**Caso:** {current_case['title']} · "
        f"**Estado:** {current_case['status']}"
    )

with head2:
    st.metric("Nota final", final_grade_label)
    st.metric("Resultado global", global_label)
    st.metric("Revisiones docentes", review_count)

# ---------------------------------------------------------
# Resumen principal
# ---------------------------------------------------------
st.divider()
st.header("1. Resultado general")

res1, res2, res3 = st.columns(3)

with res1:
    st.metric("Nota final", final_grade_label)

with res2:
    st.metric("Descriptor global", global_label)

with res3:
    st.metric("Posición global", ranking_position)

st.write(f"**Estado de revisión docente:** {review_status}")
if result_is_provisional:
    st.warning(
        "Este resultado se entrega como provisional. Puede cambiar si el equipo "
        "docente valida revisiones pendientes o actualiza el ranking."
    )
else:
    st.success("Este resultado se entrega como final para el caso cerrado.")

st.info(
    "La nota final combina lectura cuantitativa y cualitativa. "
    "No depende solo de la cantidad de intervenciones, sino de la calidad "
    "global del proceso."
)

activity1, activity2, activity3, activity4 = st.columns(4)

with activity1:
    st.metric("Intervenciones", participation_summary["interventions"])

with activity2:
    st.metric("Respuestas", participation_summary["responses"])

with activity3:
    st.metric("Hilos usados", participation_summary["threads_used"])

with activity4:
    st.metric("Evidencias", participation_summary["evidences"])

# ---------------------------------------------------------
# Resultados por componente
# ---------------------------------------------------------
st.divider()
st.header("2. Resultados por componente")

for component in result_components:
    with st.container(border=True):
        top1, top2, top3 = st.columns([2.5, 1, 1])

        with top1:
            st.write(f"**{component['name']}**")
            st.caption(f"Peso dentro de la nota final: {component['weight']}")

        with top2:
            score_label = "Pendiente" if component["score"] is None else f"{component['score']:.1f}"
            st.metric("Puntaje", score_label)

        with top3:
            st.metric("Lectura cualitativa", component["label"])

        st.progress(component["progress"] / 100.0)
        if component["score"] is None:
            st.caption("Desempeño equivalente: pendiente de evaluación")
        else:
            st.caption(f"Desempeño equivalente: {component['label']}")

# ---------------------------------------------------------
# Lectura pedagógica del resultado
# ---------------------------------------------------------
st.divider()
st.header("3. Lectura pedagógica del desempeño")

st.markdown(
    """
    Esta lectura ayuda a responder preguntas como:

    - ¿cómo me fue en general?  
    - ¿en qué componente tuve mejor desempeño?  
    - ¿qué aspecto debería fortalecer si hubiera una nueva ronda?  
    - ¿mi principal fortaleza estuvo en el rol, el argumento, la evidencia o la interacción?
    """
)

strengths = []
improvements = []

col1, col2 = st.columns(2)

with col1:
    st.subheader("Fortalezas visibles")
    if strengths:
        for item in strengths:
            st.markdown(f"- {item}")
    else:
        st.write("Todavía no se identifican fortalezas evaluativas claras.")

with col2:
    st.subheader("Aspectos por fortalecer")
    if improvements:
        for item in improvements:
            st.markdown(f"- {item}")
    else:
        st.write("Todavía no se identifican aspectos evaluativos por fortalecer.")

# ---------------------------------------------------------
# Retroalimentación final
# ---------------------------------------------------------
st.divider()
st.header("4. Retroalimentación breve final")
st.write(final_feedback)

# ---------------------------------------------------------
# Nota sobre análisis relacional
# ---------------------------------------------------------
st.divider()
st.header("5. Lectura relacional básica")

st.write(
    "En una etapa posterior, esta pantalla podrá incluir una lectura más clara "
    "de la posición del actor dentro de la red de interacciones del ejercicio."
)

st.markdown(
    """
    **Más adelante podrían verse aquí:**
    - posición general dentro del grafo  
    - intensidad básica de interacción  
    - capacidad de conexión con otros actores  
    - visualización simple del análisis relacional
    """
)

st.caption(
    "La versión dinámica y más rica del análisis de grafos se mantiene prevista para una etapa posterior."
)

# ---------------------------------------------------------
# Nota técnica
# ---------------------------------------------------------
st.divider()
st.caption(
    "Nota técnica: esta es una versión funcional inicial de la pantalla de resultados. "
    "Ya lee revisiones docentes reales por intervención y case_ranking para nota final "
    "y posición cuando existe consolidación del caso. ai_reviews, exportación y cierre "
    "formal siguen pendientes."
)
