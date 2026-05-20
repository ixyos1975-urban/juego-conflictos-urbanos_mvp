from __future__ import annotations

import streamlit as st

from config import settings
from services.auth_service import (
    mark_password_changed,
    normalize_email,
    update_current_user_password,
    validate_authenticated_access,
)
from services.progress_service import build_default_progress, get_student_progress
from services.role_service import get_assigned_role_for_user_case, get_profile_by_email

try:
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(page_title="Acceso y validación", page_icon="🔐", layout="wide")

apply_compact_academic_style()

STUDENT_PROGRESS_KEYS = [
    "guide_completed",
    "case_context_completed",
    "role_assigned",
    "role_preparation_completed",
    "public_actor_profile_completed",
    "public_actor_profile",
    "public_actor_profile_loaded_key",
    "profile_id",
    "case_id",
    "role_id",
    "assigned_role",
    "case_record",
]

st.title("Acceso y validación")
st.write(
    "Este es el primer filtro de entrada al ejercicio. "
    "Aquí se autentica el usuario con correo institucional y contraseña, "
    "y se verifica que haga parte de la lista autorizada del caso o grupo."
)

with st.expander("¿Qué se valida aquí?", expanded=True):
    st.markdown(
        f"""
        **El sistema revisa tres condiciones:**
        1. que el correo pertenezca al dominio `@{settings.allowed_email_domain}`;
        2. que la contraseña sea válida en Supabase Auth;
        3. que el usuario exista y esté activo en la lista autorizada cargada por el administrador.
        """
    )

if "access_validated" not in st.session_state:
    st.session_state["access_validated"] = False

if "validated_user_email" not in st.session_state:
    st.session_state["validated_user_email"] = ""

if "validated_user_record" not in st.session_state:
    st.session_state["validated_user_record"] = None

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "password_change_required" not in st.session_state:
    st.session_state["password_change_required"] = False


def load_student_progress_to_session(profile_id: str, case_id: str) -> None:
    ok_progress, saved_progress, progress_message = get_student_progress(
        profile_id,
        case_id,
    )

    if ok_progress and saved_progress:
        progress = {
            **build_default_progress(),
            **{
                field: bool(saved_progress.get(field))
                for field in build_default_progress()
            },
        }
        for field, value in progress.items():
            st.session_state[field] = value
    elif ok_progress:
        for field, value in build_default_progress().items():
            st.session_state.setdefault(field, value)
    else:
        st.warning(progress_message)


def load_student_context_after_access(email: str, record: dict) -> None:
    if record.get("is_admin") is True:
        return

    case_slug = str(record.get("case_slug") or "").strip()
    if not case_slug:
        return

    ok_role, role_context, role_message = get_assigned_role_for_user_case(
        email,
        case_slug,
    )

    if not ok_role or role_context is None:
        st.warning(role_message)
        return

    st.session_state["profile_id"] = role_context["profile_id"]
    st.session_state["case_id"] = role_context["case_id"]
    st.session_state["role_id"] = role_context["role_id"]
    st.session_state["assigned_role"] = role_context["assigned_role"]
    st.session_state["case_record"] = role_context["case"]
    st.session_state["role_assigned"] = True
    st.session_state["user_role"] = (
        role_context.get("profile", {}).get("user_role") or "estudiante"
    )

    load_student_progress_to_session(
        role_context["profile_id"],
        role_context["case_id"],
    )


def load_admin_context_after_access(email: str, record: dict) -> None:
    if record.get("is_admin") is not True:
        return

    ok_profile, profile_record, profile_message = get_profile_by_email(email)

    if not ok_profile or profile_record is None:
        st.warning(profile_message)
        return

    st.session_state["profile_id"] = profile_record.get("id", "")
    st.session_state["user_role"] = profile_record.get("user_role", "")


def complete_access_session(email: str, record: dict, previous_email: str = "") -> None:
    if previous_email and previous_email != email:
        for key in STUDENT_PROGRESS_KEYS:
            st.session_state.pop(key, None)

    safe_record = {
        key: value
        for key, value in record.items()
        if key not in ("auth_access_token", "auth_refresh_token")
    }

    st.session_state["access_validated"] = True
    st.session_state["authenticated"] = True
    st.session_state["password_change_required"] = False
    st.session_state["validated_user_email"] = email
    st.session_state["validated_user_record"] = safe_record
    st.session_state["user_email"] = email
    st.session_state["user_id"] = record.get("auth_user_id", "")
    st.session_state["full_name"] = record.get("full_name", "")
    st.session_state["user_type"] = record.get("user_type", "")
    st.session_state["is_admin"] = record.get("is_admin") is True

    load_student_context_after_access(email, record)
    load_admin_context_after_access(email, record)

    st.session_state.pop("pending_password_change_email", None)
    st.session_state.pop("pending_password_change_record", None)
    st.session_state.pop("pending_auth_access_token", None)
    st.session_state.pop("pending_auth_refresh_token", None)


default_email = st.session_state.get("validated_user_email", "")

with st.form("access_validation_form"):
    email = st.text_input(
        "Correo institucional",
        value=default_email,
        placeholder=f"usuario@{settings.allowed_email_domain}",
    )
    password = st.text_input(
        "Contraseña",
        type="password",
        placeholder="Ingrese su contraseña",
    )
    submitted = st.form_submit_button("Ingresar")

if submitted:
    clean_email = normalize_email(email)
    previous_email = st.session_state.get("validated_user_email", "")
    ok, record, message = validate_authenticated_access(clean_email, password)

    if ok:
        if previous_email and previous_email != clean_email:
            for key in STUDENT_PROGRESS_KEYS:
                st.session_state.pop(key, None)

        must_change_password = record.get("must_change_password") is True

        if must_change_password:
            st.session_state["access_validated"] = False
            st.session_state["authenticated"] = True
            st.session_state["password_change_required"] = True
            st.session_state["validated_user_email"] = clean_email
            st.session_state["validated_user_record"] = None
            st.session_state["user_email"] = clean_email
            st.session_state["user_id"] = record.get("auth_user_id", "")
            st.session_state["full_name"] = record.get("full_name", "")
            st.session_state["user_type"] = record.get("user_type", "")
            st.session_state["user_role"] = ""
            st.session_state["is_admin"] = record.get("is_admin") is True
            st.session_state["pending_password_change_email"] = clean_email
            st.session_state["pending_password_change_record"] = record
            st.session_state["pending_auth_access_token"] = record.get(
                "auth_access_token", ""
            )
            st.session_state["pending_auth_refresh_token"] = record.get(
                "auth_refresh_token", ""
            )
            st.warning(
                "Debe cambiar la contraseña temporal antes de continuar con el ejercicio."
            )
        else:
            complete_access_session(clean_email, record, previous_email)
            st.success(message)
    else:
        st.session_state["access_validated"] = False
        st.session_state["authenticated"] = False
        st.session_state["password_change_required"] = False
        st.session_state["validated_user_email"] = clean_email
        st.session_state["validated_user_record"] = None
        st.session_state["user_email"] = ""
        st.session_state["user_id"] = ""
        st.session_state["full_name"] = ""
        st.session_state["user_type"] = ""
        st.session_state["user_role"] = ""
        st.session_state["is_admin"] = False
        st.session_state.pop("pending_password_change_email", None)
        st.session_state.pop("pending_password_change_record", None)
        st.session_state.pop("pending_auth_access_token", None)
        st.session_state.pop("pending_auth_refresh_token", None)
        st.error(message)

st.divider()

if st.session_state.get("password_change_required"):
    st.subheader("Cambio obligatorio de contraseña")
    st.info(
        "Su cuenta fue creada con una contraseña temporal. Para continuar, "
        "defina una nueva contraseña personal."
    )

    with st.form("required_password_change_form"):
        new_password = st.text_input(
            "Nueva contraseña",
            type="password",
            placeholder="Mínimo 8 caracteres",
        )
        confirm_password = st.text_input(
            "Confirmar nueva contraseña",
            type="password",
            placeholder="Repita la nueva contraseña",
        )
        password_submitted = st.form_submit_button("Cambiar contraseña y continuar")

    if password_submitted:
        if not new_password or not confirm_password:
            st.warning("Debe ingresar y confirmar la nueva contraseña.")
        elif new_password != confirm_password:
            st.warning("Las contraseñas no coinciden.")
        elif len(new_password) < 8:
            st.warning("La nueva contraseña debe tener al menos 8 caracteres.")
        else:
            access_token = st.session_state.get("pending_auth_access_token", "")
            refresh_token = st.session_state.get("pending_auth_refresh_token", "")
            ok_update, update_message = update_current_user_password(
                access_token,
                refresh_token,
                new_password,
            )

            if not ok_update:
                st.error(update_message)
            else:
                pending_email = st.session_state.get("pending_password_change_email", "")
                ok_mark, mark_message = mark_password_changed(
                    pending_email,
                    access_token,
                    refresh_token,
                )

                if not ok_mark:
                    st.error(mark_message)
                else:
                    pending_record = (
                        st.session_state.get("pending_password_change_record") or {}
                    )
                    pending_record["must_change_password"] = False
                    complete_access_session(pending_email, pending_record)
                    st.success(
                        "Contraseña actualizada correctamente. Ya puede continuar "
                        "con el flujo del ejercicio."
                    )

    st.stop()

st.divider()
st.subheader("Estado de la validación")

if st.session_state["access_validated"]:
    st.success("El acceso fue validado correctamente.")

    record = st.session_state["validated_user_record"] or {}

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Correo validado**")
        st.write(st.session_state["validated_user_email"])

        st.markdown("**Nombre registrado**")
        st.write(record.get("full_name", "No disponible"))

        st.markdown("**Estado**")
        st.write("Habilitado")

    with col2:
        st.markdown("**Tipo de usuario**")
        st.write(record.get("user_type", "No definido"))

        st.markdown("**Grupo**")
        st.write(record.get("group_name", "No definido"))

        st.markdown("**Caso o slug asociado**")
        st.write(record.get("case_slug", "No definido"))

        st.markdown("**Observaciones**")
        st.write(record.get("notes", "Sin observaciones"))

    st.info(
        "Siguiente paso sugerido del flujo: "
        "entrar a la Guía inicial del ejercicio."
    )
else:
    st.warning(
        "Todavía no hay una validación exitosa. "
        "Revise el correo y confirme que el usuario esté en la lista autorizada."
    )

st.divider()
st.subheader("Nota técnica para la implementación")

st.markdown(
    """
    Para que esta pantalla funcione completamente, Supabase debe tener una tabla
    llamada **`allowed_users`** con información básica de usuarios autorizados
    y cada usuario debe existir previamente en Supabase Auth.

    **Campos mínimos recomendados:**
    - `email`
    - `full_name`
    - `is_active`

    **Campos opcionales útiles:**
    - `group_name`
    - `case_slug`
    - `notes`
    - `is_admin`
    - `user_type`
    """
)
