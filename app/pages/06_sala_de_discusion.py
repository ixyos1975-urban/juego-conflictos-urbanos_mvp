from __future__ import annotations

import streamlit as st

try:
    from services.case_service import is_case_interaction_closed
    from services.discussion_service import (
        create_intervention,
        get_interventions_for_thread,
        get_threads_for_case,
    )
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.case_service import is_case_interaction_closed
    from app.services.discussion_service import (
        create_intervention,
        get_interventions_for_thread,
        get_threads_for_case,
    )
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Sala de discusión",
    page_icon="💬",
    layout="wide",
)

apply_compact_academic_style()

st.title("Sala de discusión")
st.write(
    "Este es el entorno central de interacción del ejercicio. "
    "Aquí el estudiante podrá leer hilos, revisar intervenciones "
    "y publicar nuevas participaciones dentro del caso."
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
    st.warning("Antes de entrar a la sala de discusión, debe completarse el acceso y validación.")
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
        "Antes de entrar a la sala de discusión, falta completar: "
        + ", ".join(missing_onboarding_steps)
        + "."
    )
    st.stop()

# ---------------------------------------------------------
# Datos base
# ---------------------------------------------------------
profile = st.session_state.get("public_actor_profile", {})
assigned_role = st.session_state.get("assigned_role", {}) or {}
profile_id = st.session_state.get("profile_id", "")
case_id = st.session_state.get("case_id", "")
role_id = st.session_state.get("role_id", "")
case_record = st.session_state.get("case_record", {}) or {}
case_interaction_closed = is_case_interaction_closed(case_record)

if not profile_id or not case_id or not role_id:
    st.error(
        "No fue posible identificar el usuario, el caso y el rol activo para "
        "cargar la sala de discusión."
    )
    st.stop()

if case_interaction_closed:
    st.session_state.pop("reply_to_intervention_id", None)
    st.session_state.pop("reply_to_intervention_label", None)
    st.session_state.pop("reply_to_intervention_type", None)
    st.warning(
        "Ejercicio cerrado: la sala queda disponible en modo solo lectura. "
        "Ya no es posible publicar nuevas intervenciones ni responder."
    )

ok_threads, threads, threads_message = get_threads_for_case(case_id)

if not ok_threads:
    st.error(threads_message)
    st.stop()

if not threads:
    st.info("Todavía no hay hilos de discusión configurados para este caso.")
    st.stop()

thread_map = {thread["title"]: thread for thread in threads}

# ---------------------------------------------------------
# Selección de hilo
# ---------------------------------------------------------
st.divider()
st.header("1. Selección del hilo de discusión")

left, right = st.columns([1, 2])

with left:
    selected_thread_title = st.selectbox(
        "Seleccione un hilo",
        options=list(thread_map.keys()),
    )

    selected_thread = thread_map[selected_thread_title]

    st.subheader("Resumen del hilo")
    st.write(f"**Tipo:** {selected_thread['thread_type']}")
    st.write(selected_thread["description"])

with right:
    st.subheader("Qué se espera en este espacio")
    st.markdown(
        """
        Aquí podrá:
        - leer intervenciones ya publicadas;
        - responder a otros actores;
        - contraargumentar;
        - plantear posturas;
        - y, más adelante, enlazar evidencias de forma directa.

        El objetivo no es solo intervenir, sino hacerlo con coherencia, claridad y sentido estratégico.
        """
    )

# ---------------------------------------------------------
# Intervenciones del hilo
# ---------------------------------------------------------
st.divider()
st.header("2. Intervenciones del hilo")

ok_posts, current_posts, posts_message = get_interventions_for_thread(selected_thread["id"])

if not ok_posts:
    st.error(posts_message)
    current_posts = []


def get_post_labels(post):
    author_label = (
        profile.get("display_name") or "Actor del estudiante"
        if post.get("author_id") == profile_id
        else "Actor participante"
    )
    role_label = (
        assigned_role.get("name") or "Rol asignado"
        if post.get("role_id") == role_id
        else "Rol participante"
    )
    return author_label, role_label


def build_reply_label(post, author_label, role_label):
    reply_fragment = (post.get("content") or "").strip().replace("\n", " ")
    if len(reply_fragment) > 80:
        reply_fragment = reply_fragment[:77].rstrip() + "..."
    return (
        f"{author_label} | {role_label} | "
        f"{post['intervention_type']} — {reply_fragment or 'Intervención sin texto'}"
    )


def sort_posts_by_created_at(posts):
    return sorted(posts, key=lambda item: str(item.get("created_at") or ""))


def get_interaction_state(main_post, replies):
    ordered_conversation = sort_posts_by_created_at([main_post] + replies)
    ordered_replies = sort_posts_by_created_at(replies)
    last_post = ordered_conversation[-1] if ordered_conversation else main_post
    main_is_own = main_post.get("author_id") == profile_id
    has_student_reply = any(reply.get("author_id") == profile_id for reply in ordered_replies)
    last_is_own = last_post.get("author_id") == profile_id

    if main_is_own and not ordered_replies:
        return "🟢 Atendida"

    if not main_is_own and not has_student_reply:
        return "🔴 Pendiente"

    if last_is_own:
        return "🟢 Atendida"

    return "🟡 En proceso"


def get_orphan_interaction_state(post):
    if post.get("author_id") == profile_id:
        return "🟢 Atendida"
    return "🔴 Pendiente"


def render_intervention_card(post, is_reply=False, interaction_state=None):
    author_label, role_label = get_post_labels(post)
    is_own_intervention = post.get("author_id") == profile_id
    with st.container(border=True):
        top_col1, top_col2, top_col3 = st.columns([2, 2, 1])

        with top_col1:
            st.write(f"**Autor visible:** {author_label}")
            st.caption(f"Rol: {role_label}")
            if is_own_intervention:
                st.caption("🟢 Tu intervención")

        with top_col2:
            if is_reply:
                st.write("**Respuesta**")
                st.caption("Asociada a una intervención previa")
                if interaction_state:
                    st.caption(interaction_state)
            else:
                st.write(f"**Tipo de intervención:** {post['intervention_type'].capitalize()}")
                if interaction_state:
                    st.caption(interaction_state)

        with top_col3:
            st.caption(post["created_at"])

        st.write(post["content"])

        reply_label = build_reply_label(post, author_label, role_label)

        if not case_interaction_closed and st.button(
            "Responder a esta intervención",
            key=f"reply_to_{post['id']}",
            use_container_width=True,
        ):
            st.session_state["reply_to_intervention_id"] = post["id"]
            st.session_state["reply_to_intervention_label"] = reply_label
            st.session_state["reply_to_intervention_type"] = "respuesta"
            st.rerun()


posts_by_id = {post["id"]: post for post in current_posts if post.get("id")}
main_posts = [post for post in current_posts if not post.get("parent_intervention_id")]
main_post_ids = {post["id"] for post in main_posts if post.get("id")}
replies_by_parent = {post["id"]: [] for post in main_posts if post.get("id")}
orphan_replies = []

for post in current_posts:
    parent_id = post.get("parent_intervention_id")
    if not parent_id:
        continue

    root_id = parent_id
    seen_ids = {post.get("id")}

    while root_id in posts_by_id and posts_by_id[root_id].get("parent_intervention_id"):
        if root_id in seen_ids:
            break
        seen_ids.add(root_id)
        root_id = posts_by_id[root_id].get("parent_intervention_id")

    if root_id in main_post_ids:
        replies_by_parent.setdefault(root_id, []).append(post)
    else:
        orphan_replies.append(post)

if not current_posts:
    st.info("Todavía no hay intervenciones en este hilo.")
else:
    for post in main_posts:
        replies = replies_by_parent.get(post["id"], [])
        ordered_replies = sort_posts_by_created_at(replies)
        interaction_state = get_interaction_state(post, ordered_replies)
        render_intervention_card(post, interaction_state=interaction_state)

        if replies:
            st.caption("Respuestas asociadas")
            for reply in ordered_replies:
                spacer, reply_area = st.columns([0.08, 0.92])
                with reply_area:
                    render_intervention_card(reply, is_reply=True)

    if orphan_replies:
        st.subheader("Respuestas sin intervención principal visible")
        for reply in sort_posts_by_created_at(orphan_replies):
            render_intervention_card(
                reply,
                is_reply=True,
                interaction_state=get_orphan_interaction_state(reply),
            )

# ---------------------------------------------------------
# Publicación de nueva intervención
# ---------------------------------------------------------
st.divider()
st.header("3. Publicar nueva intervención")

if case_interaction_closed:
    st.info(
        "La participación del caso ya cerró. Puede revisar el hilo, pero no "
        "registrar nuevas intervenciones."
    )

possible_parents = {"Ninguna: intervención inicial en este hilo": None}
for index, post in enumerate(current_posts, start=1):
    fragment = (post.get("content") or "").strip().replace("\n", " ")
    if len(fragment) > 70:
        fragment = fragment[:67].rstrip() + "..."
    label = (
        f"Intervención {index} | {post['intervention_type']} — "
        f"{fragment or 'Intervención sin texto'}"
    )
    possible_parents[label] = post["id"]

reply_to_intervention_id = st.session_state.get("reply_to_intervention_id")
reply_to_intervention_label = st.session_state.get("reply_to_intervention_label", "")
reply_type_default = st.session_state.get("reply_to_intervention_type")

selected_parent_index = 0
for index, (_label, parent_id) in enumerate(possible_parents.items()):
    if parent_id == reply_to_intervention_id:
        selected_parent_index = index
        break

intervention_type_options = ["postura", "respuesta", "contraargumento", "negociacion", "cierre"]
selected_type_index = (
    intervention_type_options.index("respuesta")
    if reply_type_default == "respuesta"
    else 0
)

if reply_to_intervention_id:
    st.info(
        "Estás respondiendo a la intervención de "
        f"{reply_to_intervention_label or 'otro participante'}."
    )

with st.form("discussion_post_form"):
    intervention_type = st.selectbox(
        "Tipo de intervención",
        options=intervention_type_options,
        index=selected_type_index,
        disabled=case_interaction_closed,
    )

    parent_label = st.selectbox(
        "Intervención a la que responde (opcional)",
        options=list(possible_parents.keys()),
        index=selected_parent_index,
        disabled=case_interaction_closed,
    )

    content = st.text_area(
        "Contenido de la intervención",
        height=180,
        placeholder=(
            "Escriba aquí su intervención. Procure que sea clara, coherente con el rol "
            "y lo bastante sólida para aportar a la discusión."
        ),
        disabled=case_interaction_closed,
    )

    submitted = st.form_submit_button(
        "Publicar intervención",
        disabled=case_interaction_closed,
    )

if submitted and not case_interaction_closed:
    clean_content = content.strip()
    parent_id = possible_parents[parent_label]
    clean_intervention_type = (
        "respuesta"
        if reply_to_intervention_id and parent_id == reply_to_intervention_id
        else intervention_type
    )

    if not clean_content:
        st.error("Debe escribir el contenido de la intervención antes de publicarla.")
    else:
        intervention_phase = selected_thread.get("phase") or "apertura"
        ok_create, _created_intervention, create_message = create_intervention(
            case_id=case_id,
            thread_id=selected_thread["id"],
            author_id=profile_id,
            role_id=role_id,
            intervention_type=clean_intervention_type,
            content=clean_content,
            parent_intervention_id=parent_id,
            phase=intervention_phase,
        )

        if ok_create:
            st.session_state.pop("reply_to_intervention_id", None)
            st.session_state.pop("reply_to_intervention_label", None)
            st.session_state.pop("reply_to_intervention_type", None)
            st.success(
                "La intervención fue registrada correctamente en esta versión funcional inicial. "
                "Recargue la página o vuelva a seleccionar el hilo para verla en el listado."
            )
        else:
            st.error(create_message)

# ---------------------------------------------------------
# Orientación de uso
# ---------------------------------------------------------
st.divider()
st.header("4. Recomendaciones para esta fase")

st.markdown(
    """
    - antes de publicar, revise el hilo seleccionado;  
    - procure mantener coherencia con el rol;  
    - responda con claridad y no de forma impulsiva;  
    - use evidencias cuando sea pertinente;  
    - recuerde que el objetivo no es solo hablar, sino sostener una posición.
    """
)

st.info(
    "En una etapa posterior, esta sala de discusión se conectará a la base de datos, "
    "permitirá navegación más rica entre respuestas y enlazará evidencias reales."
)

st.divider()
st.caption(
    "Nota técnica: esta es una versión funcional inicial de la sala de discusión. "
    "Más adelante se integrarán servicios de lectura y escritura reales desde Supabase."
)
