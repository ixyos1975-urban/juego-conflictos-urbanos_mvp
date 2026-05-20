from __future__ import annotations

import streamlit as st

try:
    from services.progress_service import upsert_student_progress
    from services.profile_service import (
        build_empty_profile,
        get_profile_for_user_case,
        normalize_profile_data,
        submit_profile_for_user_case,
        upsert_profile_for_user_case,
    )
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.services.progress_service import upsert_student_progress
    from app.services.profile_service import (
        build_empty_profile,
        get_profile_for_user_case,
        normalize_profile_data,
        submit_profile_for_user_case,
        upsert_profile_for_user_case,
    )
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Perfil público del actor",
    page_icon="🪪",
    layout="wide",
)

apply_compact_academic_style()

st.title("Perfil público del actor")
st.write(
    "En esta pantalla el estudiante construye la presentación pública del actor "
    "que representará dentro del ejercicio. El propósito no es cambiar el rol, "
    "sino darle una forma más consistente y visible para la comunidad del juego."
)

# ---------------------------------------------------------
# Validación del flujo previo
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
guide_completed = st.session_state.get("guide_completed", False)
case_context_completed = st.session_state.get("case_context_completed", False)
role_preparation_completed = st.session_state.get("role_preparation_completed", False)
validated_user_record = st.session_state.get("validated_user_record", {}) or {}

if not access_validated:
    st.warning("Antes de entrar aquí, debe completarse el acceso y validación.")
    st.stop()

if validated_user_record.get("is_admin") is True:
    st.info(
        "Este usuario tiene perfil administrativo. Para continuar, ingrese al "
        "Panel administrativo."
    )
    st.stop()

if not guide_completed:
    st.warning("Antes de continuar, debe completarse la Guía inicial del ejercicio.")
    st.stop()

if not case_context_completed:
    st.warning("Antes de continuar, debe revisarse el contexto del caso.")
    st.stop()

if not role_preparation_completed:
    st.warning(
        "Antes de construir el perfil público, debe revisarse el rol y realizar "
        "la preparación inicial."
    )
    st.stop()

if "public_actor_profile_completed" not in st.session_state:
    st.session_state["public_actor_profile_completed"] = False

if "public_actor_profile" not in st.session_state:
    st.session_state["public_actor_profile"] = build_empty_profile()

validated_user_email = st.session_state.get("validated_user_email", "")
case_slug = str(validated_user_record.get("case_slug") or "").strip()

if not validated_user_email or not case_slug:
    st.error(
        "No fue posible identificar el usuario validado y el caso activo para "
        "guardar el perfil publico del actor."
    )
    st.stop()

profile_cache_key = f"{validated_user_email}|{case_slug}"
loaded_profile_cache_key = st.session_state.get("public_actor_profile_loaded_key")

if loaded_profile_cache_key != profile_cache_key:
    ok_profile, saved_profile, profile_message = get_profile_for_user_case(
        validated_user_email,
        case_slug,
    )

    if ok_profile and saved_profile:
        st.session_state["public_actor_profile"] = normalize_profile_data(saved_profile)
        st.session_state["public_actor_profile_completed"] = True
        st.session_state["public_actor_profile_loaded_key"] = profile_cache_key
    elif ok_profile:
        st.session_state["public_actor_profile"] = build_empty_profile()
        st.session_state["public_actor_profile_completed"] = False
        st.session_state["public_actor_profile_loaded_key"] = profile_cache_key
    elif not ok_profile:
        st.warning(profile_message)

profile = st.session_state["public_actor_profile"]
profile_status = profile.get("profile_status") or "draft"
profile_is_submitted = profile_status == "submitted"

st.success(
    "Flujo correcto: acceso validado, guía leída, contexto revisado "
    "y preparación inicial del rol completada."
)

st.divider()

# ---------------------------------------------------------
# Explicación breve
# ---------------------------------------------------------
st.header("1. ¿Qué debe hacer aquí?")
st.write(
    "Aquí debe construir una presentación breve y coherente del actor que "
    "representará. Esta información será su perfil visible dentro del ejercicio."
)

st.info(
    "El rol no cambia. Lo que usted define aquí es la manera en que ese actor "
    "se presenta públicamente y cómo orienta su entrada inicial a la discusión."
)

# ---------------------------------------------------------
# Formulario de perfil
# ---------------------------------------------------------
st.header("2. Construcción del perfil público")

if profile_is_submitted:
    st.success(
        "Estado del perfil: enviado definitivamente. "
        "El perfil está bloqueado para edición."
    )
    st.info("El perfil se muestra en modo lectura.")
else:
    st.info("Estado del perfil: borrador editable.")

    with st.form("public_actor_profile_form"):
        display_name = st.text_input(
            "Nombre visible del actor",
            value=profile.get("display_name", ""),
            placeholder="Ejemplo: Vocería de residentes del barrio",
        )

        avatar_url = st.text_input(
            "Enlace de imagen o avatar (opcional)",
            value=profile.get("avatar_url", ""),
            placeholder="https://...",
        )

        public_presentation = st.text_area(
            "Presentación pública breve",
            value=profile.get("public_presentation", ""),
            height=100,
            placeholder=(
                "Describa brevemente quién es este actor dentro del conflicto y "
                "qué representa frente a la comunidad del juego."
            ),
        )

        initial_position = st.text_area(
            "Postura inicial frente al conflicto",
            value=profile.get("initial_position", ""),
            height=100,
            placeholder=(
                "Explique de manera breve cuál es la posición inicial de este actor "
                "frente al caso."
            ),
        )

        col1, col2 = st.columns(2)

        with col1:
            main_interest = st.text_area(
                "Interés principal que defenderá",
                value=profile.get("main_interest", ""),
                height=90,
                placeholder="¿Cuál es el interés principal que este actor buscará defender?",
            )

        with col2:
            non_negotiable_point = st.text_area(
                "Punto no negociable",
                value=profile.get("non_negotiable_point", ""),
                height=90,
                placeholder="¿Qué aspecto no puede ceder este actor dentro de la discusión?",
            )

        action_line = st.text_area(
            "Línea de acción inicial",
            value=profile.get("action_line", ""),
            height=90,
            placeholder=(
                "Describa brevemente cómo piensa actuar este actor en la primera etapa "
                "del ejercicio."
            ),
        )

        submitted = st.form_submit_button("Guardar borrador")

    if submitted:
        profile_data = {
            "display_name": display_name.strip(),
            "avatar_url": avatar_url.strip(),
            "public_presentation": public_presentation.strip(),
            "initial_position": initial_position.strip(),
            "main_interest": main_interest.strip(),
            "non_negotiable_point": non_negotiable_point.strip(),
            "action_line": action_line.strip(),
        }

        required_fields = [
            "display_name",
            "public_presentation",
            "initial_position",
            "main_interest",
            "non_negotiable_point",
            "action_line",
        ]

        missing_labels = {
            "display_name": "Nombre visible del actor",
            "public_presentation": "Presentación pública breve",
            "initial_position": "Postura inicial frente al conflicto",
            "main_interest": "Interés principal",
            "non_negotiable_point": "Punto no negociable",
            "action_line": "Línea de acción inicial",
        }

        missing = [missing_labels[key] for key in required_fields if not profile_data[key]]

        if missing:
            st.error(
                "Aún faltan campos por completar: " + ", ".join(missing) + "."
            )
        else:
            ok_save, saved_profile, save_message = upsert_profile_for_user_case(
                validated_user_email,
                case_slug,
                profile_data,
            )

            if not ok_save:
                st.error(save_message)
                st.stop()

            profile_data = normalize_profile_data(saved_profile or profile_data)
            st.session_state["public_actor_profile"] = profile_data
            st.session_state["public_actor_profile_completed"] = True
            st.session_state["public_actor_profile_loaded_key"] = profile_cache_key
            profile_id = st.session_state.get("profile_id", "")
            case_id = st.session_state.get("case_id", "")
            if profile_id and case_id:
                ok_progress, _saved_progress, progress_message = upsert_student_progress(
                    profile_id,
                    case_id,
                    public_actor_profile_completed=True,
                )
                if not ok_progress:
                    st.warning(progress_message)
            st.success(
                "El borrador del perfil público del actor fue guardado correctamente. "
                "Cuando esté listo, puede enviarlo definitivamente."
            )

    st.warning(
        "El envío definitivo bloqueará la edición del perfil para el estudiante."
    )
    if st.button("Enviar perfil definitivo"):
        ok_submit, submitted_profile, submit_message = submit_profile_for_user_case(
            validated_user_email,
            case_slug,
        )

        if not ok_submit:
            st.error(submit_message)
            st.stop()

        st.session_state["public_actor_profile"] = normalize_profile_data(
            submitted_profile or profile
        )
        st.session_state["public_actor_profile_loaded_key"] = profile_cache_key
        st.success("El perfil público fue enviado definitivamente.")
        st.rerun()

st.divider()

# ---------------------------------------------------------
# Vista previa
# ---------------------------------------------------------
st.header("3. Vista previa del perfil público")

current_profile = st.session_state["public_actor_profile"]

preview_col1, preview_col2 = st.columns([1, 2])

with preview_col1:
    st.subheader("Identidad visible")
    st.write(current_profile.get("display_name") or "Sin definir")
    if current_profile.get("avatar_url"):
        st.caption("Imagen o avatar registrado")
        st.code(current_profile["avatar_url"], language=None)
    else:
        st.caption("Sin imagen o avatar registrado")

with preview_col2:
    st.subheader("Presentación")
    st.write(current_profile.get("public_presentation") or "Sin definir")

    st.subheader("Postura inicial")
    st.write(current_profile.get("initial_position") or "Sin definir")

    st.subheader("Interés principal")
    st.write(current_profile.get("main_interest") or "Sin definir")

    st.subheader("Punto no negociable")
    st.write(current_profile.get("non_negotiable_point") or "Sin definir")

    st.subheader("Línea de acción")
    st.write(current_profile.get("action_line") or "Sin definir")

st.divider()

# ---------------------------------------------------------
# Estado final de esta fase
# ---------------------------------------------------------
st.header("4. Estado de esta fase")

if st.session_state["public_actor_profile_completed"]:
    st.success(
        "El perfil público del actor ya está completo. "
        "Siguiente pantalla sugerida: Panel principal del estudiante."
    )
else:
    st.warning(
        "Todavía falta completar y guardar el perfil público para continuar "
        "de manera adecuada con el flujo."
    )

st.divider()
st.caption(
    "Nota técnica: esta es una versión funcional inicial. Más adelante, "
    "el perfil deberá guardarse y leerse desde la base de datos."
)
