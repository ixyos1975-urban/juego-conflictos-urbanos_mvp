"""Servicios para resolver el rol real asignado al estudiante."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from services.case_service import get_case_by_slug
    from services.supabase_client import get_supabase_client
except ModuleNotFoundError:
    from app.services.case_service import get_case_by_slug
    from app.services.supabase_client import get_supabase_client


def _as_list(value: Any) -> List[str]:
    """Normaliza campos que pueden venir como lista, texto o nulos."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if not value:
        return []

    return [line.strip("- ").strip() for line in str(value).splitlines() if line.strip()]


def _first_present(record: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
    """Devuelve el primer valor presente entre varias llaves posibles."""
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def get_profile_by_email(
    email: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca el perfil del usuario por correo."""
    if not email or not str(email).strip():
        return False, None, "No se recibio un correo valido para consultar el perfil."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar el perfil porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_profile_by_email_secure",
                {"p_email": str(email).strip().lower()},
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, "No se encontro un perfil asociado al correo validado."

        return True, rows[0], "Perfil encontrado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar el perfil en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_role_assignment_for_user_case(
    profile_id: str,
    case_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca la asignacion de rol usando role_assignments.user_id + case_id."""
    if not profile_id or not str(profile_id).strip():
        return False, None, "No se recibio un profile_id valido para consultar el rol."

    if not case_id or not str(case_id).strip():
        return False, None, "No se recibio un case_id valido para consultar el rol."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar la asignacion de rol porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_role_assignment_for_user_case_secure",
                {
                    "p_profile_id": str(profile_id).strip(),
                    "p_case_id": str(case_id).strip(),
                },
            )
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, (
                "No se encontro una asignacion de rol para este usuario y caso."
            )

        return True, rows[0], "Asignacion de rol encontrada correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar la asignacion de rol en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def get_role_by_id(
    role_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Busca la ficha completa del rol."""
    if not role_id or not str(role_id).strip():
        return False, None, "No se recibio un role_id valido para consultar el rol."

    client = get_supabase_client()

    if client is None:
        return False, None, (
            "No fue posible consultar el rol porque aun no hay credenciales "
            "validas de Supabase."
        )

    try:
        result = (
            client.table("roles")
            .select("*")
            .eq("id", str(role_id).strip())
            .limit(1)
            .execute()
        )

        rows = result.data or []

        if not rows:
            return False, None, "No se encontro la ficha del rol asignado."

        return True, rows[0], "Rol encontrado correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, None, (
            "No fue posible consultar el rol en Supabase. "
            f"Detalle tecnico: {exc}"
        )


def build_role_context(
    role_record: Dict[str, Any],
    assignment_record: Dict[str, Any],
) -> Dict[str, Any]:
    """Convierte el registro de rol en la estructura que consume la pantalla."""
    role_name = _first_present(role_record, ["name", "title", "role_name"], "Rol asignado")

    return {
        "id": role_record.get("id"),
        "assignment_id": assignment_record.get("id"),
        "name": role_name,
        "actor_type": _first_present(
            role_record,
            ["actor_type", "type", "category"],
            "No definido",
        ),
        "mission": _first_present(
            role_record,
            ["mission", "description", "public_description"],
            "",
        ),
        "interests": _as_list(
            _first_present(role_record, ["interests", "main_interests"], [])
        ),
        "constraints": _as_list(
            _first_present(role_record, ["constraints", "limitations"], [])
        ),
        "resources": _as_list(
            _first_present(role_record, ["resources", "capacities"], [])
        ),
        "non_negotiable_points": _as_list(
            _first_present(
                role_record,
                ["non_negotiable_points", "non_negotiables", "red_lines"],
                [],
            )
        ),
        "success_criteria": _first_present(
            role_record,
            ["success_criteria", "evaluation_focus", "objective"],
            "",
        ),
    }


def get_assigned_role_for_user_case(
    email: str,
    case_slug: str,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Resuelve perfil, caso, asignacion y ficha completa del rol."""
    ok_profile, profile_record, profile_message = get_profile_by_email(email)
    if not ok_profile or profile_record is None:
        return False, None, profile_message

    ok_case, case_record, case_message = get_case_by_slug(case_slug)
    if not ok_case or case_record is None:
        return False, None, case_message

    profile_id = profile_record.get("id")
    case_id = case_record.get("id")

    ok_assignment, assignment_record, assignment_message = (
        get_role_assignment_for_user_case(profile_id, case_id)
    )
    if not ok_assignment or assignment_record is None:
        return False, None, assignment_message

    role_id = assignment_record.get("role_id")

    ok_role, role_record, role_message = get_role_by_id(role_id)
    if not ok_role or role_record is None:
        return False, None, role_message

    assigned_role = build_role_context(role_record, assignment_record)

    return True, {
        "profile": profile_record,
        "case": case_record,
        "assignment": assignment_record,
        "role": role_record,
        "assigned_role": assigned_role,
        "profile_id": profile_id,
        "case_id": case_id,
        "role_id": role_id,
    }, "Rol asignado resuelto correctamente."


def get_students_with_roles_for_case(
    case_id: str,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Lista estudiantes con su rol asignado para un caso."""
    if not case_id or not str(case_id).strip():
        return False, [], "No se recibio un case_id valido para consultar estudiantes."

    client = get_supabase_client()

    if client is None:
        return False, [], (
            "No fue posible consultar estudiantes porque aun no hay "
            "credenciales validas de Supabase."
        )

    try:
        result = (
            client.rpc(
                "get_students_with_roles_for_case_secure",
                {"p_case_id": str(case_id).strip()},
            )
            .execute()
        )

        students = result.data or []

        if not students:
            return True, [], "No hay estudiantes con rol asignado para este caso."

        active_students = []
        for student in students:
            email = str(student.get("email") or "").strip().lower()
            profile_id = str(student.get("profile_id") or "").strip()

            if not email or not profile_id:
                continue

            allowed_result = (
                client.rpc(
                    "get_allowed_user_by_email_secure",
                    {"p_email": email},
                )
                .execute()
            )
            allowed_rows = allowed_result.data or []
            allowed_user = allowed_rows[0] if allowed_rows else {}

            if allowed_user.get("is_active") is not True:
                continue

            if str(allowed_user.get("user_type") or "").strip().lower() != "student":
                continue

            assignment_result = (
                client.rpc(
                    "get_role_assignment_for_user_case_secure",
                    {
                        "p_profile_id": profile_id,
                        "p_case_id": str(case_id).strip(),
                    },
                )
                .execute()
            )
            assignment_rows = assignment_result.data or []
            assignment = assignment_rows[0] if assignment_rows else {}

            if (
                str(assignment.get("participation_status") or "")
                .strip()
                .lower()
                != "active"
            ):
                continue

            active_students.append(student)

        if not active_students:
            return True, [], "No hay estudiantes activos con rol asignado para este caso."

        return True, active_students, "Estudiantes activos con rol cargados correctamente."

    except Exception as exc:  # noqa: BLE001
        return False, [], (
            "No fue posible consultar estudiantes con rol en Supabase. "
            f"Detalle tecnico: {exc}"
        )
