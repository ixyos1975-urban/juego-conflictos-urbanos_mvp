from __future__ import annotations

import pandas as pd
import streamlit as st

from services.case_service import build_case_context, get_case_by_slug
from services.case_material_service import (
    get_case_materials_for_user,
    group_materials_by_type,
)
from services.progress_service import upsert_student_progress

try:
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Contexto del caso",
    page_icon="🗺️",
    layout="wide",
)

apply_compact_academic_style()

st.title("Contexto del caso")
st.write(
    "Esta pantalla presenta el escenario general del conflicto urbano. "
    "Su función es ayudar a entender el problema antes de entrar a la "
    "fase de rol y preparación específica del actor."
)

# ---------------------------------------------------------
# Validación básica del flujo
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
guide_completed = st.session_state.get("guide_completed", False)
validated_user = st.session_state.get("validated_user_record", {}) or {}

if not access_validated:
    st.warning(
        "Antes de entrar al contexto del caso, debe completarse primero "
        "la pantalla de acceso y validación."
    )
    st.stop()

if validated_user.get("is_admin") is True:
    st.info(
        "Este usuario tiene perfil administrativo. Para continuar, ingrese al "
        "Panel administrativo."
    )
    st.stop()

if not guide_completed:
    st.warning(
        "Antes de continuar, debe leerse y marcarse como completada la "
        "Guía inicial del ejercicio."
    )
    st.stop()

if "case_context_completed" not in st.session_state:
    st.session_state["case_context_completed"] = False

case_slug = str(
    validated_user.get("case_slug") or st.session_state.get("case_slug", "")
).strip()

if not case_slug:
    st.error("No fue posible identificar el caso activo para cargar el contexto.")
    st.stop()

case_record = st.session_state.get("case_record", {}) or {}

if not case_record:
    ok_case, saved_case, case_message = get_case_by_slug(case_slug)
    if not ok_case or saved_case is None:
        st.error(case_message)
        st.stop()
    case_record = saved_case
    st.session_state["case_record"] = case_record

case_context = build_case_context(case_record)
pending_context_message = "Información pendiente de ser definida por el docente."
validated_user_email = st.session_state.get("validated_user_email", "")

ok_materials, case_materials, materials_message = get_case_materials_for_user(
    validated_user_email,
    case_slug,
)

if not ok_materials:
    st.warning(materials_message)
    case_materials = []

materials_by_type = group_materials_by_type(case_materials)


def render_materials(materials):
    if not materials:
        st.info("No hay materiales registrados para esta categoría.")
        return

    for material in materials:
        with st.container(border=True):
            st.write(f"**{material.get('title') or 'Material sin título'}**")
            if material.get("source_name"):
                st.caption(f"Fuente: {material['source_name']}")
            if material.get("description"):
                st.write(material["description"])
            if material.get("content_text"):
                with st.expander("Leer material completo", expanded=False):
                    st.write(material["content_text"])
            if material.get("external_url"):
                st.markdown(f"[Abrir enlace externo]({material['external_url']})")
            if material.get("file_url"):
                st.markdown(f"[Abrir archivo]({material['file_url']})")


def render_case_map(case_context):
    latitude = case_context.get("map_center_lat")
    longitude = case_context.get("map_center_lng")

    if latitude is None or longitude is None:
        st.info("No hay coordenadas registradas para visualizar el mapa del caso.")
        return

    map_data = pd.DataFrame(
        [{"lat": float(latitude), "lon": float(longitude)}]
    )
    st.map(map_data, latitude="lat", longitude="lon", zoom=14)

st.success("Flujo correcto: acceso validado y guía inicial completada.")

st.divider()

# ---------------------------------------------------------
# Encabezado general del caso
# ---------------------------------------------------------
st.header("1. Presentación general del conflicto")

st.subheader(case_context["title"])
st.write(case_context["description"] or pending_context_message)

# ---------------------------------------------------------
# Bloque descriptivo principal
# ---------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Descripción general")
    st.write(case_context["description"] or pending_context_message)

    st.subheader("Contexto territorial")
    st.write(case_context["territorial_context"] or pending_context_message)

with col2:
    st.subheader("Ubicación general")
    st.write(case_context["location_name"] or pending_context_message)

    st.subheader("Estado del caso")
    st.write(f"Fase: {case_context['phase']}")
    st.write(f"Estado: {case_context['status']}")

st.divider()

# ---------------------------------------------------------
# Materiales de contexto
# ---------------------------------------------------------
st.header("2. Materiales de contexto")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Mapa o ubicación", "Notas de prensa", "Blogs y referencias", "Documentos base"]
)

with tab1:
    render_case_map(case_context)
    render_materials(materials_by_type.get("mapa", []))
    st.caption(
        "Estos materiales ayudan a ubicar espacialmente el conflicto y sus áreas "
        "de referencia."
    )

with tab2:
    render_materials(materials_by_type.get("nota_prensa", []))
    st.caption(
        "Las notas de prensa sirven como insumo de contexto, no como conclusión "
        "única sobre el caso."
    )

with tab3:
    render_materials(materials_by_type.get("referencia", []))
    st.caption("Estas referencias amplían la lectura inicial del conflicto.")

with tab4:
    render_materials(
        materials_by_type.get("documento_base", [])
        + materials_by_type.get("normativa", [])
        + materials_by_type.get("otro", [])
    )

    st.subheader("Reglas del ejercicio")
    st.write(case_context["rules"] or pending_context_message)

    st.subheader("Criterios de evaluación")
    st.write(case_context["evaluation_criteria"] or pending_context_message)

st.divider()

# ---------------------------------------------------------
# Claves de lectura del caso
# ---------------------------------------------------------
st.header("3. Claves de lectura del caso")

st.markdown(
    """
    Antes de pasar al rol, el estudiante debería salir de esta pantalla con claridad sobre:

    - cuál es el problema principal del caso;  
    - qué tensiones están en juego;  
    - qué actores podrían verse implicados;  
    - qué información adicional conviene revisar;  
    - y por qué este conflicto merece ser discutido.
    """
)

st.warning(
    "Esta pantalla no le dice todavía qué actor le corresponde representar. "
    "Primero le ayuda a comprender el escenario general."
)

# ---------------------------------------------------------
# Confirmación de comprensión básica
# ---------------------------------------------------------
st.divider()
st.header("4. Confirmación de lectura del contexto")

st.write(
    "Cuando considere que ya entendió el escenario general del conflicto, "
    "puede marcar esta pantalla como revisada para continuar al siguiente paso."
)

if st.button("He revisado el contexto general del caso"):
    st.session_state["case_context_completed"] = True
    profile_id = st.session_state.get("profile_id", "")
    case_id = st.session_state.get("case_id", "")
    if profile_id and case_id:
        ok_progress, _saved_progress, progress_message = upsert_student_progress(
            profile_id,
            case_id,
            case_context_completed=True,
        )
        if not ok_progress:
            st.warning(progress_message)
    st.success(
        "El contexto del caso quedó marcado como revisado. "
        "El siguiente paso recomendado es entrar a la pantalla del rol y preparación inicial."
    )

if st.session_state["case_context_completed"]:
    st.info(
        "Estado actual: contexto del caso revisado. "
        "Siguiente pantalla sugerida: Mi rol y preparación inicial."
    )

st.divider()
st.caption(
    "Nota técnica: esta pantalla lee la información base disponible en la tabla "
    "del caso activo. Los materiales complementarios podrán ampliarse en una "
    "etapa posterior."
)
