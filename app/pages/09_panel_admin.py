from __future__ import annotations

import streamlit as st

try:
    from config import settings
    from services.ai import generate_ai_review_for_intervention
    from services.case_service import get_case_by_slug
    from services.discussion_service import get_case_discussion_summary
    from services.evidence_service import get_evidence_counts_for_case, get_evidences_for_user
    from services.review_service import (
        get_case_ranking_for_case,
        get_ai_reviews_for_case,
        get_interventions_for_teacher_review,
        get_teacher_reviews_for_student,
        refresh_case_ranking_for_case,
        upsert_ai_review,
        upsert_teacher_review,
    )
    from services.role_service import get_profile_by_email, get_students_with_roles_for_case
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.config import settings
    from app.services.ai import generate_ai_review_for_intervention
    from app.services.case_service import get_case_by_slug
    from app.services.discussion_service import get_case_discussion_summary
    from app.services.evidence_service import get_evidence_counts_for_case, get_evidences_for_user
    from app.services.review_service import (
        get_case_ranking_for_case,
        get_ai_reviews_for_case,
        get_interventions_for_teacher_review,
        get_teacher_reviews_for_student,
        refresh_case_ranking_for_case,
        upsert_ai_review,
        upsert_teacher_review,
    )
    from app.services.role_service import get_profile_by_email, get_students_with_roles_for_case
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Panel administrativo",
    page_icon="🛠️",
    layout="wide",
)

apply_compact_academic_style()

st.title("Panel administrativo")
st.write(
    "Esta pantalla concentra el seguimiento general del ejercicio, la lectura "
    "preliminar del sistema, la validación docente y la preparación del cierre."
)

# ---------------------------------------------------------
# Validación básica de acceso
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
validated_user = st.session_state.get("validated_user_record", {}) or {}

if not access_validated or not validated_user:
    st.warning(
        "Antes de entrar al panel administrativo, debe completarse el acceso y validación."
    )
    st.stop()

is_admin = validated_user.get("is_admin") is True

if not is_admin:
    st.error(
        "Acceso restringido. Este panel está disponible solo para usuarios "
        "administradores autorizados."
    )
    st.stop()

st.divider()

# ---------------------------------------------------------
# Datos reales disponibles
# ---------------------------------------------------------
case_slug = str(validated_user.get("case_slug") or st.session_state.get("case_slug", "")).strip()

if not case_slug:
    st.error("No fue posible identificar el caso activo para cargar el panel administrativo.")
    st.stop()

ok_case, case_record, case_message = get_case_by_slug(case_slug)

if not ok_case or case_record is None:
    st.error(case_message)
    st.stop()

case_id = case_record.get("id")

ok_discussion, discussion_summary, discussion_message = get_case_discussion_summary(case_id)
if not ok_discussion:
    st.warning(discussion_message)

ok_evidences, evidence_summary, evidence_message = get_evidence_counts_for_case(case_id)
if not ok_evidences:
    st.warning(evidence_message)

ok_students, students_real, students_message = get_students_with_roles_for_case(case_id)
if not ok_students:
    st.warning(students_message)
    students_real = []

validated_user_email = st.session_state.get("validated_user_email", "")

ok_review_interventions, review_interventions, review_interventions_message = (
    get_interventions_for_teacher_review(case_id)
)
if not ok_review_interventions:
    st.warning(review_interventions_message)
    review_interventions = []

active_student_profile_ids = {
    str(student.get("profile_id"))
    for student in students_real
    if student.get("profile_id")
}
review_interventions = [
    intervention
    for intervention in review_interventions
    if str(intervention.get("author_id") or "") in active_student_profile_ids
]

ok_ai_reviews, ai_reviews, ai_reviews_message = get_ai_reviews_for_case(case_id)
if not ok_ai_reviews:
    st.warning(ai_reviews_message)
    ai_reviews = []

ok_case_ranking, case_ranking, case_ranking_message = get_case_ranking_for_case(case_id)
if not ok_case_ranking:
    st.warning(case_ranking_message)
    case_ranking = []

teacher_reviews_by_intervention = {}
teacher_review_load_errors = []
for student_record in students_real:
    student_profile_id = student_record.get("profile_id")
    if not student_profile_id:
        continue

    ok_student_reviews, student_reviews, student_reviews_message = (
        get_teacher_reviews_for_student(case_id, student_profile_id)
    )
    if not ok_student_reviews:
        teacher_review_load_errors.append(student_reviews_message)
        continue

    for review in student_reviews:
        review_intervention_id = review.get("intervention_id")
        if review_intervention_id:
            teacher_reviews_by_intervention[str(review_intervention_id)] = review

if teacher_review_load_errors:
    st.warning(
        "No fue posible cargar todas las revisiones docentes existentes para "
        "calcular el semaforo de intervenciones."
    )

ai_reviews_by_intervention = {
    str(review.get("intervention_id")): review
    for review in ai_reviews
    if review.get("intervention_id")
}

interventions_by_author = discussion_summary.get("interventions_by_author", {})
evidences_by_author = evidence_summary.get("evidences_by_author", {})

case_summary = {
    "title": case_record.get("title") or case_record.get("slug") or "Caso activo",
    "phase": case_record.get("phase") or "No definida",
    "status": case_record.get("status") or "No definido",
    "participants": len(students_real),
    "active_threads": discussion_summary.get("active_threads", 0),
    "total_posts": discussion_summary.get("total_interventions", 0),
    "total_evidences": evidence_summary.get("total_evidences", 0),
}

students = []
for student in students_real:
    profile_id = student.get("profile_id")
    students.append({
        "profile_id": profile_id,
        "name": student.get("name") or student.get("email") or "Estudiante",
        "email": student.get("email") or "",
        "role": student.get("role") or "Rol asignado",
        "interventions": interventions_by_author.get(profile_id, 0),
        "evidences": evidences_by_author.get(profile_id, 0),
        "preliminary_status": "Pendiente de revisión",
        "final_grade": "Pendiente",
    })

rating_options = {
    "Excelente": "excelente",
    "Sobresaliente": "sobresaliente",
    "Bueno": "bueno",
    "Regular": "regular",
    "Pobre": "pobre",
}
discussion_result_options = {
    "Ganada": "ganada",
    "Empatada": "empatada",
    "Perdida": "perdida",
    "No definida": "no_definida",
}
review_status_options = {
    "Pendiente": "pendiente",
    "Validada": "validada",
    "Observada": "observada",
}
argument_strength_options = {
    "Alta": "alta",
    "Media": "media",
    "Baja": "baja",
}
argument_type_options = {
    "Técnico": "tecnico",
    "Normativo": "normativo",
    "Comunitario": "comunitario",
    "Económico": "economico",
    "Ambiental": "ambiental",
    "Político": "politico",
    "Mixto": "mixto",
    "Indefinido": "indefinido",
}
moderation_status_options = {
    "Normal": "normal",
    "Alerta": "alerta",
    "Revisión": "revision",
}
role_coherence_options = {
    "Alta": "alta",
    "Media": "media",
    "Baja": "baja",
}
review_state_options = {
    "Todas": None,
    "Pendientes": "pendiente",
    "En proceso": "en_proceso",
    "Revisadas": "revisada",
}
review_state_labels = {
    "pendiente": "🔴 Pendiente",
    "en_proceso": "🟡 En proceso",
    "revisada": "🟢 Revisada",
}
ai_state_options = {
    "Todas": None,
    "Sin lectura AI": "sin_ai",
    "AI generada": "ai_generada",
    "AI integrada": "ai_integrada",
}
ai_state_labels = {
    "sin_ai": "🔴 Sin lectura AI",
    "ai_generada": "🟡 AI generada",
    "ai_integrada": "🟢 AI integrada",
}


def _label_for_value(options: dict[str, str], value: str) -> str:
    for label, option_value in options.items():
        if option_value == value:
            return label
    return next(iter(options.keys()))


def _intervention_id(intervention: dict) -> str:
    return str(intervention.get("id") or intervention.get("intervention_id") or "")


def _review_state_for_intervention(intervention: dict) -> str:
    intervention_id = _intervention_id(intervention)
    teacher_review = teacher_reviews_by_intervention.get(intervention_id)

    if teacher_review and teacher_review.get("review_status") == "validada":
        return "revisada"

    if teacher_review or intervention_id in ai_reviews_by_intervention:
        return "en_proceso"

    return "pendiente"


def _review_state_label(state: str) -> str:
    return review_state_labels.get(state, review_state_labels["pendiente"])


def _ai_state_for_intervention(intervention: dict) -> str:
    intervention_id = _intervention_id(intervention)
    teacher_review = teacher_reviews_by_intervention.get(intervention_id)

    if (
        intervention_id in ai_reviews_by_intervention
        and teacher_review
        and teacher_review.get("review_status") == "validada"
    ):
        return "ai_integrada"

    if intervention_id in ai_reviews_by_intervention:
        return "ai_generada"

    return "sin_ai"


def _ai_state_label(state: str) -> str:
    return ai_state_labels.get(state, ai_state_labels["sin_ai"])


review_state_counts = {
    "pendiente": 0,
    "en_proceso": 0,
    "revisada": 0,
}
ai_state_counts = {
    "sin_ai": 0,
    "ai_generada": 0,
    "ai_integrada": 0,
}
review_state_counts_by_author = {}
for intervention in review_interventions:
    state = _review_state_for_intervention(intervention)
    ai_state = _ai_state_for_intervention(intervention)
    review_state_counts[state] = review_state_counts.get(state, 0) + 1
    ai_state_counts[ai_state] = ai_state_counts.get(ai_state, 0) + 1
    author_id = intervention.get("author_id")
    if author_id:
        review_state_counts_by_author.setdefault(
            author_id,
            {"pendiente": 0, "en_proceso": 0, "revisada": 0},
        )
        review_state_counts_by_author[author_id][state] += 1

# ---------------------------------------------------------
# Encabezado administrativo
# ---------------------------------------------------------
st.header("1. Estado general del caso")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Caso activo", case_summary["title"])

with col2:
    st.metric("Fase", case_summary["phase"])

with col3:
    st.metric("Estado", case_summary["status"])

with col4:
    st.metric("Participantes", case_summary["participants"])

col5, col6, col7 = st.columns(3)

with col5:
    st.metric("Hilos activos", case_summary["active_threads"])

with col6:
    st.metric("Intervenciones registradas", case_summary["total_posts"])

with col7:
    st.metric("Evidencias registradas", case_summary["total_evidences"])

# ---------------------------------------------------------
# Seguimiento general
# ---------------------------------------------------------
st.divider()
st.header("2. Seguimiento general del grupo")

st.write(
    "Este bloque permite revisar, de manera rápida, cómo va el grupo "
    "en términos de participación y estado preliminar del proceso."
)

if not students:
    st.warning("Todavía no hay estudiantes con rol asignado para este caso.")
else:
    for student in students:
        with st.container(border=True):
            a, b, c, d, e = st.columns([2, 2, 1, 1, 1])

            with a:
                st.write(f"**{student['name']}**")
                st.caption(student["role"])

            with b:
                st.write(f"Intervenciones: {student['interventions']}")
                st.write(f"Evidencias: {student['evidences']}")

            with c:
                st.write("Estado preliminar")
                st.write(student["preliminary_status"])

            with d:
                st.write("Nota final")
                st.write(student["final_grade"])

            with e:
                st.button("Ver detalle", key=f"detail_{student['profile_id']}")

# ---------------------------------------------------------
# Lectura preliminar del sistema
# ---------------------------------------------------------
st.divider()
st.header("3. Valoraciones preliminares del sistema")

st.write(
    "Aquí podrán verse lecturas automáticas o semi-automáticas del proceso, "
    "que después deberán ser revisadas y, si hace falta, ajustadas por el docente."
)

st.caption(
    "Estas lecturas son apoyo preliminar del sistema. No reemplazan la revisión "
    "docente, no generan nota final y no alimentan ranking ni consolidación."
)

if not ai_reviews:
    st.info("Todavía no hay lecturas preliminares de IA registradas para este caso.")
else:
    for item in ai_reviews:
        with st.container(border=True):
            x, y, z = st.columns([2, 2, 2])

            with x:
                st.write(f"**Estudiante:** {item.get('author_name') or 'Estudiante'}")
                st.caption(item.get("role_name") or "Rol asignado")
                st.caption(item.get("thread_title") or "Hilo sin título")

            with y:
                st.write("**Lectura preliminar:**")
                st.write(f"Fuerza argumentativa: {item.get('argument_strength', 'No definida')}")
                st.write(f"Tipo: {item.get('argument_type', 'No definido')}")
                st.write(f"Coherencia de rol: {item.get('role_coherence', 'No definida')}")
                st.write(f"Moderación: {item.get('moderation_status', 'No definida')}")

            with z:
                st.write("**Acción docente sugerida:**")
                if item.get("moderation_status") in ("alerta", "revision"):
                    st.write("Priorizar revisión docente de esta intervención.")
                else:
                    st.write("Usar como insumo preliminar de lectura.")

st.write("**Registrar o actualizar lectura preliminar asistida**")

st.markdown(
    """
<style>
div[data-testid="stMarkdownContainer"]:has(#ai-help-expander-anchor)
  + div[data-testid="stExpander"] details {
    border: 1px solid #eadb9c;
    border-radius: 8px;
    background: #fffdf2;
}

div[data-testid="stMarkdownContainer"]:has(#ai-help-expander-anchor)
  + div[data-testid="stExpander"] summary {
    background: #fff4bf;
    border-radius: 8px;
    padding: 0.45rem 0.7rem;
}

div[data-testid="stMarkdownContainer"]:has(#ai-help-expander-anchor)
  + div[data-testid="stExpander"] summary p {
    color: #302b18;
    font-weight: 700;
    font-size: 0.94rem;
}
</style>
<span id="ai-help-expander-anchor"></span>
""",
    unsafe_allow_html=True,
)

with st.expander("ℹ️ **¿CÓMO USAR LA LECTURA PRELIMINAR IA?**", expanded=False):
    st.markdown(
        """
<div style="
    background: #fff8db;
    border: 1px solid #eadb9c;
    border-radius: 8px;
    padding: 0.9rem 1rem;
    color: #302b18;
    font-size: 0.92rem;
    line-height: 1.45;
">
  <div style="
      font-size: 0.98rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      margin-bottom: 0.55rem;
  ">
    USO DOCENTE DE LA LECTURA PRELIMINAR IA
  </div>

  <p style="margin: 0 0 0.65rem 0;">
    La lectura preliminar IA es un apoyo analítico para orientar la revisión
    docente de cada intervención. No reemplaza la evaluación del profesor ni
    genera una nota final automática.
  </p>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">1. Tipo de argumento</p>
  <ul style="margin: 0 0 0.55rem 1rem; padding-left: 0.6rem;">
    <li><strong>Comunitario:</strong> permanencia barrial, afectación social, desplazamiento, redes comunitarias, vida cotidiana, participación o justicia espacial.</li>
    <li><strong>Técnico:</strong> implantación, movilidad, cargas urbanísticas, mitigación, servicios, accesibilidad o impacto físico-espacial.</li>
    <li><strong>Normativo:</strong> normas, POT, tratamientos urbanísticos, obligaciones regulatorias, acuerdos, artículos o instrumentos formales.</li>
    <li><strong>Mixto:</strong> solo cuando existe equilibrio real entre dos o más dimensiones argumentativas.</li>
    <li><strong>Indefinido:</strong> texto demasiado general, ambiguo o sin una dimensión argumentativa clara.</li>
  </ul>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">2. Fuerza argumentativa</p>
  <ul style="margin: 0 0 0.55rem 1rem; padding-left: 0.6rem;">
    <li><strong>Baja:</strong> intervención genérica, poco desarrollada o sin sustento claro.</li>
    <li><strong>Media:</strong> intervención clara, con una idea reconocible, aunque sin evidencia fuerte.</li>
    <li><strong>Alta:</strong> intervención bien estructurada, con soporte claro y desarrollo argumentativo sólido.</li>
  </ul>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">3. Evidencia detectada</p>
  <p style="margin: 0 0 0.55rem 0;">
    La evidencia solo debe considerarse presente cuando el texto incluye datos,
    normas, fuentes, casos concretos, referencias explícitas o instrumentos
    identificables.
  </p>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">4. Puntaje preliminar</p>
  <p style="margin: 0 0 0.55rem 0;">
    El puntaje preliminar es orientativo. Debe leerse junto con el comentario IA
    y nunca sustituye la revisión docente.
  </p>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">5. Revisión docente</p>
  <p style="margin: 0 0 0.55rem 0;">
    Antes de guardar la lectura preliminar, el docente debe revisar si la
    clasificación, la fuerza argumentativa, la evidencia y el comentario son
    coherentes con la intervención.
  </p>

  <p style="margin: 0.55rem 0 0.2rem 0; font-weight: 700;">6. No debe hacerse</p>
  <ul style="margin: 0 0 0 1rem; padding-left: 0.6rem;">
    <li>No usar la lectura IA como nota final automática.</li>
    <li>No guardar una lectura preliminar sin revisión docente.</li>
    <li>No confundir <code>ai_reviews</code> con <code>teacher_reviews</code>.</li>
    <li>No usar el resultado IA para actualizar directamente el ranking.</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

ai_status_col1, ai_status_col2, ai_status_col3 = st.columns(3)
with ai_status_col1:
    st.metric("🔴 Sin lectura AI", ai_state_counts["sin_ai"])
with ai_status_col2:
    st.metric("🟡 AI generada", ai_state_counts["ai_generada"])
with ai_status_col3:
    st.metric("🟢 AI integrada", ai_state_counts["ai_integrada"])

selected_ai_state_filter_label = st.selectbox(
    "Filtrar intervenciones por estado de lectura AI",
    options=list(ai_state_options.keys()),
    key="ai_review_state_filter",
)
selected_ai_state_filter = ai_state_options[selected_ai_state_filter_label]

ai_generation_message = st.session_state.pop("ai_generation_message", None)
if ai_generation_message:
    st.info(ai_generation_message)

if not settings.ai_enabled:
    st.caption(
        "La generacion automatica AI esta desactivada. El registro manual sigue disponible."
    )

st.session_state.setdefault("ai_prompt_version", settings.ai_prompt_version)

ai_intervention_options = {}
ai_intervention_records = {}
for intervention in review_interventions:
    ai_state = _ai_state_for_intervention(intervention)
    if selected_ai_state_filter and ai_state != selected_ai_state_filter:
        continue

    intervention_id = intervention.get("id") or intervention.get("intervention_id")
    if not intervention_id:
        continue

    content_fragment = (
        intervention.get("content") or intervention.get("title") or ""
    ).strip()
    if len(content_fragment) > 70:
        content_fragment = content_fragment[:67].rstrip() + "..."

    label = (
        f"{_ai_state_label(ai_state)} | "
        f"{intervention.get('author_name', 'Estudiante')} | "
        f"{intervention.get('thread_title', 'Hilo sin título')} | "
        f"{intervention.get('intervention_type', 'intervención')} — "
        f"{content_fragment or 'Intervención sin texto'}"
    )
    if intervention.get("created_at"):
        label = f"{label} | {intervention['created_at']}"

    if label in ai_intervention_options:
        label = f"{label} ({len(ai_intervention_options) + 1})"

    normalized_intervention = {
        **intervention,
        "id": str(intervention_id),
        "intervention_id": str(intervention_id),
        "case_id": intervention.get("case_id") or case_id,
        "author_name": intervention.get("author_name") or "Estudiante",
        "author_email": intervention.get("author_email") or "",
        "role_name": intervention.get("role_name") or "Rol asignado",
        "thread_id": intervention.get("thread_id") or "",
        "thread_title": intervention.get("thread_title") or "Hilo sin titulo",
        "content": intervention.get("content") or intervention.get("title") or "",
    }
    ai_intervention_options[label] = str(intervention_id)
    ai_intervention_records[str(intervention_id)] = normalized_intervention

pending_ai_prefill = st.session_state.pop("pending_ai_prefill", None)
if pending_ai_prefill:
    st.session_state["ai_argument_strength"] = _label_for_value(
        argument_strength_options,
        pending_ai_prefill["argument_strength"],
    )
    st.session_state["ai_argument_type"] = _label_for_value(
        argument_type_options,
        pending_ai_prefill["argument_type"],
    )
    st.session_state["ai_role_coherence"] = _label_for_value(
        role_coherence_options,
        pending_ai_prefill["role_coherence"],
    )
    st.session_state["ai_moderation_status"] = _label_for_value(
        moderation_status_options,
        pending_ai_prefill["moderation_status"],
    )
    st.session_state["ai_evidence_detected"] = pending_ai_prefill[
        "evidence_detected"
    ]
    st.session_state["ai_preliminary_score"] = pending_ai_prefill[
        "preliminary_score"
    ]
    st.session_state["ai_teacher_review_recommended"] = pending_ai_prefill[
        "teacher_review_recommended"
    ]
    st.session_state["ai_comment"] = pending_ai_prefill["ai_comment"]
    st.session_state["ai_prompt_version"] = pending_ai_prefill["prompt_version"]

with st.form("admin_ai_review_form"):
    if ai_intervention_options:
        selected_ai_intervention_label = st.selectbox(
            "Seleccione una intervención para lectura preliminar",
            options=list(ai_intervention_options.keys()),
            key="ai_review_intervention",
        )
    else:
        selected_ai_intervention_label = None
        st.warning("No hay intervenciones disponibles para lectura preliminar.")

    argument_strength_label = st.selectbox(
        "Fuerza argumentativa",
        options=list(argument_strength_options.keys()),
        index=1,
        key="ai_argument_strength",
    )
    argument_type_label = st.selectbox(
        "Tipo de argumento",
        options=list(argument_type_options.keys()),
        index=7,
        key="ai_argument_type",
    )
    role_coherence_label = st.selectbox(
        "Coherencia con el rol",
        options=list(role_coherence_options.keys()),
        index=1,
        key="ai_role_coherence",
    )
    moderation_status_label = st.selectbox(
        "Estado de moderación",
        options=list(moderation_status_options.keys()),
        index=0,
        key="ai_moderation_status",
    )

    evidence_detected = st.checkbox(
        "Evidencia detectada en la intervencion",
        key="ai_evidence_detected",
    )
    preliminary_score = st.number_input(
        "Puntaje preliminar",
        min_value=0.0,
        max_value=5.0,
        step=0.1,
        key="ai_preliminary_score",
    )
    teacher_review_recommended = st.checkbox(
        "Recomendar revision docente prioritaria",
        key="ai_teacher_review_recommended",
    )
    ai_comment = st.text_area(
        "Comentario preliminar AI",
        key="ai_comment",
    )
    prompt_version = st.text_input(
        "Version de prompt",
        key="ai_prompt_version",
    )

    generate_col, save_col = st.columns(2)
    with generate_col:
        submitted_ai_generation = st.form_submit_button(
            "Generar lectura AI",
            disabled=not settings.ai_enabled or not bool(ai_intervention_options),
        )
    with save_col:
        submitted_ai_review = st.form_submit_button(
            "Guardar lectura preliminar",
        )

if submitted_ai_generation:
    selected_ai_intervention_id = (
        ai_intervention_options.get(selected_ai_intervention_label)
        if selected_ai_intervention_label
        else None
    )
    selected_intervention = ai_intervention_records.get(str(selected_ai_intervention_id))

    if not selected_intervention:
        st.error("Debe existir una intervencion real para generar la lectura AI.")
    else:
        ok_generated, generated_review, generated_message = (
            generate_ai_review_for_intervention(selected_intervention, case_record)
        )
        if ok_generated and generated_review:
            st.session_state["pending_ai_prefill"] = generated_review
            st.session_state["ai_generation_message"] = (
                "Lectura AI generada y precargada. Revise y ajuste antes de guardar."
            )
            st.rerun()
        else:
            st.error(generated_message)

if submitted_ai_review:
    selected_ai_intervention_id = (
        ai_intervention_options.get(selected_ai_intervention_label)
        if selected_ai_intervention_label
        else None
    )

    if not selected_ai_intervention_id:
        st.error("Debe existir una intervención real para guardar la lectura preliminar.")
    else:
        ok_ai_save, _saved_ai_review, ai_save_message = upsert_ai_review(
            intervention_id=selected_ai_intervention_id,
            argument_strength=argument_strength_options[argument_strength_label],
            argument_type=argument_type_options[argument_type_label],
            moderation_status=moderation_status_options[moderation_status_label],
            role_coherence=role_coherence_options[role_coherence_label],
            evidence_detected=evidence_detected,
            preliminary_score=preliminary_score,
            teacher_review_recommended=teacher_review_recommended,
            ai_comment=ai_comment,
            prompt_version=prompt_version,
        )

        if ok_ai_save:
            st.success("Lectura preliminar de IA guardada correctamente.")
        else:
            st.error(ai_save_message)

st.warning(
    "Estas valoraciones no deben entenderse como cierre definitivo. "
    "Su función es apoyar la revisión, no reemplazarla."
)

# ---------------------------------------------------------
# Validación docente por rúbrica
# ---------------------------------------------------------
st.divider()
st.header("4. Validación docente por rúbrica")

st.write(
    "Esta sección permite registrar una revisión docente por intervención real. "
    "La consolidación acumulativa del resultado queda pendiente para una etapa posterior."
)

status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    st.metric("🔴 Pendientes", review_state_counts["pendiente"])
with status_col2:
    st.metric("🟡 En proceso", review_state_counts["en_proceso"])
with status_col3:
    st.metric("🟢 Revisadas", review_state_counts["revisada"])

selected_review_state_filter_label = st.selectbox(
    "Filtrar intervenciones por estado de revisión",
    options=list(review_state_options.keys()),
    key="teacher_review_state_filter",
)
selected_review_state_filter = review_state_options[selected_review_state_filter_label]

student_options = {}
for index, student in enumerate(students, start=1):
    student_label = student["name"]
    if student.get("email") and student["email"] != student_label:
        student_label = f"{student_label} ({student['email']})"
    if student_label in student_options:
        student_label = f"{student_label} #{index}"
    student_options[student_label] = student.get("profile_id")

if not student_options:
    student_options = {"No disponible todavía": None}

selected_student = st.selectbox(
    "Seleccione un estudiante para revisar",
    options=list(student_options.keys()),
    key="teacher_review_student",
)
selected_student_profile_id = student_options.get(selected_student)

selected_student_counts = review_state_counts_by_author.get(
    selected_student_profile_id,
    {"pendiente": 0, "en_proceso": 0, "revisada": 0},
)
st.caption(
    "Estado del estudiante seleccionado: "
    f"🔴 pendientes {selected_student_counts['pendiente']} | "
    f"🟡 en proceso {selected_student_counts['en_proceso']} | "
    f"🟢 revisadas {selected_student_counts['revisada']}"
)

filtered_review_interventions = [
    intervention
    for intervention in review_interventions
    if selected_student_profile_id
    and intervention.get("author_id") == selected_student_profile_id
    and (
        selected_review_state_filter is None
        or _review_state_for_intervention(intervention) == selected_review_state_filter
    )
]

with st.form("admin_rubric_review_form"):
    intervention_options = {}
    for intervention in filtered_review_interventions:
        review_state = _review_state_for_intervention(intervention)
        content_fragment = (
            intervention.get("content") or intervention.get("title") or ""
        ).strip()
        if len(content_fragment) > 70:
            content_fragment = content_fragment[:67].rstrip() + "..."

        label = (
            f"{_review_state_label(review_state)} | "
            f"{intervention.get('thread_title', 'Hilo sin título')} | "
            f"{intervention.get('intervention_type', 'intervención')} — "
            f"{content_fragment or 'Intervención sin texto'}"
        )
        if intervention.get("created_at"):
            label = f"{label} | {intervention['created_at']}"

        if label in intervention_options:
            label = f"{label} ({len(intervention_options) + 1})"

        intervention_options[label] = intervention.get("id") or intervention.get("intervention_id")

    if intervention_options:
        selected_intervention_label = st.selectbox(
            "Seleccione una intervención para revisar",
            options=list(intervention_options.keys()),
        )
    else:
        selected_intervention_label = None
        st.warning("No hay intervenciones disponibles para revisión docente de este estudiante.")

    selected_preview_intervention_id = (
        intervention_options.get(selected_intervention_label)
        if selected_intervention_label
        else None
    )
    selected_preview_intervention = next(
        (
            intervention
            for intervention in filtered_review_interventions
            if str(intervention.get("id") or intervention.get("intervention_id") or "")
            == str(selected_preview_intervention_id)
        ),
        None,
    )

    if selected_preview_intervention:
        st.write("**Intervención seleccionada / texto a evaluar**")
        with st.container(border=True):
            meta1, meta2, meta3 = st.columns([2, 2, 1])
            with meta1:
                st.write(
                    f"**Estudiante:** "
                    f"{selected_preview_intervention.get('author_name') or selected_student}"
                )
                st.caption(
                    f"Rol: {selected_preview_intervention.get('role_name') or 'Rol asignado'}"
                )
            with meta2:
                st.write(
                    f"**Hilo:** "
                    f"{selected_preview_intervention.get('thread_title') or 'Hilo sin título'}"
                )
                st.caption(
                    "Tipo: "
                    f"{selected_preview_intervention.get('intervention_type') or 'intervención'}"
                )
            with meta3:
                st.caption(selected_preview_intervention.get("created_at") or "Sin fecha")

            st.markdown("**Texto completo de la intervención**")
            st.write(
                selected_preview_intervention.get("content")
                or selected_preview_intervention.get("title")
                or "Intervención sin texto registrado."
            )

            antecedent_intervention_id = (
                selected_preview_intervention.get("parent_intervention_id")
                or selected_preview_intervention.get("reply_to_id")
                or selected_preview_intervention.get("response_to_id")
            )
            antecedent_intervention = None
            if antecedent_intervention_id:
                antecedent_intervention = next(
                    (
                        intervention
                        for intervention in review_interventions
                        if str(
                            intervention.get("id")
                            or intervention.get("intervention_id")
                            or ""
                        )
                        == str(antecedent_intervention_id)
                    ),
                    None,
                )

            st.markdown("**Contexto de respuesta**")
            if antecedent_intervention:
                st.caption(
                    "La intervención evaluada responde directamente a la "
                    "siguiente postura previa."
                )
                context1, context2, context3 = st.columns([2, 2, 1])
                with context1:
                    st.write(
                        f"**Autor antecedente:** "
                        f"{antecedent_intervention.get('author_name') or 'Actor participante'}"
                    )
                    st.caption(
                        f"Rol: {antecedent_intervention.get('role_name') or 'Rol no disponible'}"
                    )
                with context2:
                    st.write(
                        f"**Hilo:** "
                        f"{antecedent_intervention.get('thread_title') or 'Hilo sin título'}"
                    )
                    st.caption(
                        "Tipo: "
                        f"{antecedent_intervention.get('intervention_type') or 'intervención'}"
                    )
                with context3:
                    st.caption(antecedent_intervention.get("created_at") or "Sin fecha")

                st.write(
                    antecedent_intervention.get("content")
                    or antecedent_intervention.get("title")
                    or "Intervención antecedente sin texto registrado."
                )
            elif antecedent_intervention_id:
                st.caption(
                    "Esta intervención registra una antecedente directa, pero "
                    "su contenido no está disponible en el listado actual."
                )
            else:
                st.caption(
                    "Esta intervención no registra una intervención antecedente directa."
                )

            selected_intervention_evidences = []
            if selected_student_profile_id:
                ok_selected_evidences, selected_student_evidences, selected_evidences_message = (
                    get_evidences_for_user(selected_student_profile_id)
                )
                if ok_selected_evidences:
                    selected_intervention_evidences = [
                        evidence
                        for evidence in selected_student_evidences
                        if str(evidence.get("intervention_id") or "")
                        == str(selected_preview_intervention_id)
                    ]
                else:
                    st.caption(selected_evidences_message)

            st.markdown("**Evidencias asociadas**")
            if selected_intervention_evidences:
                for evidence in selected_intervention_evidences:
                    st.write(f"- {evidence.get('title') or 'Evidencia sin título'}")
                    if evidence.get("external_url"):
                        st.caption(evidence["external_url"])
            else:
                st.caption("No hay evidencias asociadas a esta intervención.")

    st.write("**Componentes de valoración**")

    intervention_score = st.selectbox(
        "Valoración general de la intervención",
        options=list(rating_options.keys()),
        index=2,
    )
    role_coherence_score = st.selectbox(
        "Coherencia con el rol",
        options=list(rating_options.keys()),
        index=2,
    )
    argument_quality_score = st.selectbox(
        "Calidad argumentativa",
        options=list(rating_options.keys()),
        index=2,
    )
    evidence_use_score = st.selectbox(
        "Uso de evidencia y sustento",
        options=list(rating_options.keys()),
        index=2,
    )

    discussion_result_label = st.selectbox(
        "Resultado de la discusión",
        options=list(discussion_result_options.keys()),
        index=3,
    )

    review_status_label = st.selectbox(
        "Estado de revisión",
        options=list(review_status_options.keys()),
        index=0,
    )

    teacher_comment = st.text_area(
        "Comentario docente breve",
        height=120,
        placeholder=(
            "Aquí podrá escribirse una retroalimentación breve que complemente "
            "la valoración cuantitativa."
        ),
    )

    submitted = st.form_submit_button("Guardar revisión docente")

if submitted:
    selected_intervention_id = (
        intervention_options.get(selected_intervention_label)
        if selected_intervention_label
        else None
    )

    if not selected_intervention_id:
        st.error("Debe existir una intervención real para guardar la revisión docente.")
    else:
        ok_reviewer, reviewer_profile, reviewer_message = get_profile_by_email(
            validated_user_email
        )

        if not ok_reviewer or reviewer_profile is None:
            st.error(
                "No fue posible identificar el perfil del docente que realiza "
                f"la revisión. {reviewer_message}"
            )
        else:
            ok_review, _saved_review, review_message = upsert_teacher_review(
                intervention_id=selected_intervention_id,
                reviewed_by=reviewer_profile["id"],
                intervention_rating=rating_options[intervention_score],
                role_coherence_rating=rating_options[role_coherence_score],
                argument_quality_rating=rating_options[argument_quality_score],
                evidence_use_rating=rating_options[evidence_use_score],
                discussion_result=discussion_result_options[discussion_result_label],
                review_status=review_status_options[review_status_label],
                teacher_comment=teacher_comment,
            )

            if ok_review:
                st.success(f"Revisión docente guardada para {selected_student}.")
            else:
                st.error(review_message)

# ---------------------------------------------------------
# Ranking consolidado
# ---------------------------------------------------------
st.divider()
st.header("5. Ranking consolidado del caso")

st.caption(
    "Este ranking usa únicamente revisiones docentes con estado validada. "
    "Las lecturas de IA no participan en este cálculo."
)

if st.button("Actualizar ranking del caso", use_container_width=True):
    ok_refresh, refreshed_rows, refresh_message = refresh_case_ranking_for_case(case_id)
    if ok_refresh:
        st.success(
            f"{refresh_message} Filas actualizadas: {refreshed_rows}."
        )
        ok_case_ranking, case_ranking, case_ranking_message = (
            get_case_ranking_for_case(case_id)
        )
        if not ok_case_ranking:
            st.warning(case_ranking_message)
            case_ranking = []
    else:
        st.error(refresh_message)

if not case_ranking:
    st.info(
        "Aún no hay ranking consolidado. Valide revisiones docentes y luego "
        "actualice el ranking del caso."
    )
else:
    for row in case_ranking:
        with st.container(border=True):
            r1, r2, r3 = st.columns([1, 3, 2])
            with r1:
                st.metric("Posición", row.get("position", "-"))
            with r2:
                st.write(f"**{row.get('student_name', 'Estudiante')}**")
                st.caption(row.get("role_name", "Rol asignado"))
            with r3:
                score = row.get("total_score")
                score_label = "No disponible" if score is None else f"{float(score):.2f}"
                st.metric("Puntaje consolidado", score_label)

# ---------------------------------------------------------
# Cierre y exportación
# ---------------------------------------------------------
st.divider()
st.header("6. Cierre del ejercicio y reportes")

st.write(
    "Este bloque queda reservado para el cierre formal del caso y la producción "
    "de reportes administrativos en una etapa posterior del MVP."
)

c1, c2, c3 = st.columns(3)

with c1:
    st.button("Resultados finales (pendiente)", use_container_width=True)

with c2:
    st.button("Entrega al estudiante (pendiente)", use_container_width=True)

with c3:
    st.button("Reporte Excel (pendiente)", use_container_width=True)

st.caption(
    "Funcionalidad pendiente: estos controles aún no ejecutan cierre formal, "
    "entrega de resultados ni exportación."
)

# ---------------------------------------------------------
# Nota técnica final
# ---------------------------------------------------------
st.divider()
st.caption(
    "Nota técnica: este panel opera sobre datos persistentes del caso activo. "
    "El acceso administrativo, las lecturas AI, las revisiones docentes y el "
    "ranking consolidado funcionan mediante servicios y RPC seguras. La lectura "
    "AI es apoyo preliminar y no reemplaza la revisión docente. El ranking se "
    "consolida por acción explícita del administrador. El cierre formal y la "
    "exportación quedan para una etapa posterior del MVP."
)
