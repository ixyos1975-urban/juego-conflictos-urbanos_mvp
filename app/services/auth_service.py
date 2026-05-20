"""Servicios básicos de autenticación y autorización para el MVP.

Esta capa separa la lógica de validación del correo institucional y la
verificación del usuario autorizado, para que la pantalla no se llene
de código difícil de leer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# Import flexible para que el archivo funcione tanto si la app corre
# desde la carpeta `app/` como si se ejecuta como paquete.
try:
    from config import settings
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.config import settings
    from app.services.supabase_client import get_supabase_client


def normalize_email(email: str) -> str:
    """Limpia espacios y normaliza el correo a minúsculas."""
    return (email or "").strip().lower()


def is_valid_institutional_email(email: str) -> Tuple[bool, str]:
    """Valida que el correo pertenezca al dominio institucional esperado."""
    normalized = normalize_email(email)

    if not normalized:
        return False, "Debe ingresar un correo institucional."

    expected_suffix = f"@{settings.allowed_email_domain}"

    if not normalized.endswith(expected_suffix):
        return (
            False,
            f"El correo debe pertenecer al dominio {expected_suffix}.",
        )

    return True, "Correo institucional válido."


def get_allowed_user_by_email(
    email: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca el usuario en la tabla `allowed_users`.

    La tabla debería existir en Supabase y, como mínimo, contener:
    - email
    - full_name
    - is_active

    Puede contener además:
    - group_name
    - case_slug
    - notes
    - is_admin
    - user_type
    """
    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar usuarios autorizados porque aún "
            "no hay credenciales válidas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_allowed_user_by_email_secure",
                {"p_email": normalize_email(email)},
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, (
                "El correo institucional es válido, pero no aparece en la "
                "lista de usuarios autorizados para este ejercicio."
            )

        record = rows[0]

        if not record.get("is_active", True):
            return False, record, (
                "El usuario fue encontrado, pero actualmente no está "
                "habilitado para ingresar al ejercicio."
            )

        return True, record, "Usuario validado y autorizado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar la lista de usuarios autorizados. "
            f"Detalle técnico: {exc}"
        )


def authenticate_with_password(
    email: str,
    password: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Autentica contra Supabase Auth usando correo y contraseña."""
    normalized_email = normalize_email(email)

    if not normalized_email:
        return False, None, "Debe ingresar un correo institucional."

    if not password:
        return False, None, "Debe ingresar la contraseña."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible autenticar porque aún no hay credenciales válidas "
            "de Supabase."
        )

    try:
        auth_response = client.auth.sign_in_with_password(
            {
                "email": normalized_email,
                "password": password,
            }
        )

        user = getattr(auth_response, "user", None)

        if user is None:
            return False, None, "Correo o contraseña incorrectos."

        user_email = normalize_email(getattr(user, "email", normalized_email))
        session = getattr(auth_response, "session", None)

        return True, {
            "user_id": str(getattr(user, "id", "")),
            "email": user_email,
            "access_token": str(getattr(session, "access_token", "") or ""),
            "refresh_token": str(getattr(session, "refresh_token", "") or ""),
        }, "Autenticación correcta."

    except Exception:  # noqa: BLE001
        return False, None, "Correo o contraseña incorrectos."


def validate_access(email: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Ejecuta la validación completa de acceso.

    Orden:
    1. valida dominio institucional;
    2. consulta lista de usuarios autorizados.
    """
    is_valid_email, message = is_valid_institutional_email(email)
    if not is_valid_email:
        return False, None, message

    return get_allowed_user_by_email(email)


def validate_authenticated_access(
    email: str,
    password: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Valida dominio, contraseña en Supabase Auth y lista autorizada."""
    normalized_email = normalize_email(email)

    is_valid_email, message = is_valid_institutional_email(normalized_email)
    if not is_valid_email:
        return False, None, message

    ok_allowed, allowed_record, allowed_message = get_allowed_user_by_email(
        normalized_email
    )
    if not ok_allowed or allowed_record is None:
        return False, None, allowed_message

    ok_auth, auth_record, auth_message = authenticate_with_password(
        normalized_email,
        password,
    )
    if not ok_auth or auth_record is None:
        return False, None, auth_message

    allowed_record["auth_user_id"] = auth_record.get("user_id", "")
    allowed_record["auth_email"] = auth_record.get("email", normalized_email)
    allowed_record["auth_access_token"] = auth_record.get("access_token", "")
    allowed_record["auth_refresh_token"] = auth_record.get("refresh_token", "")

    return True, allowed_record, "Usuario autenticado y autorizado correctamente."


def update_current_user_password(
    access_token: str,
    refresh_token: str,
    new_password: str,
) -> Tuple[bool, str]:
    """Actualiza la contraseña del usuario autenticado en Supabase Auth."""
    if not access_token or not refresh_token:
        return False, "No hay una sesión autenticada válida para cambiar la contraseña."

    if not new_password:
        return False, "Debe ingresar una nueva contraseña."

    client = get_supabase_client()

    if client is None:
        return False, (
            "No fue posible actualizar la contraseña porque aún no hay "
            "credenciales válidas de Supabase."
        )

    try:
        client.auth.set_session(access_token, refresh_token)
        client.auth.update_user({"password": new_password})
        return True, "Contraseña actualizada correctamente."
    except Exception as exc:  # noqa: BLE001
        return False, (
            "No fue posible actualizar la contraseña. "
            f"Detalle técnico: {exc}"
        )


def mark_password_changed(
    email: str,
    access_token: str = "",
    refresh_token: str = "",
) -> Tuple[bool, str]:
    """Marca en allowed_users que el usuario ya cambió su contraseña inicial."""
    normalized_email = normalize_email(email)

    if not normalized_email:
        return False, "No se recibió un correo válido para actualizar el estado."

    client = get_supabase_client()

    if client is None:
        return False, (
            "No fue posible actualizar el estado de contraseña porque aún no hay "
            "credenciales válidas de Supabase."
        )

    try:
        if access_token and refresh_token:
            client.auth.set_session(access_token, refresh_token)

        client.rpc(
            "mark_password_changed_secure",
            {"p_email": normalized_email},
        ).execute()
        return True, "Estado de contraseña actualizado correctamente."
    except Exception as exc:  # noqa: BLE001
        return False, (
            "La contraseña fue actualizada, pero no fue posible marcar el cambio "
            "en allowed_users. "
            f"Detalle técnico: {exc}"
        )
