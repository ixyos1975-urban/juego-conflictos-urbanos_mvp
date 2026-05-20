"""Punto de entrada principal de la app."""

from __future__ import annotations

import streamlit as st

try:
    from config import settings
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.config import settings
    from app.ui_styles import apply_compact_academic_style
st.set_page_config(
    page_title=settings.app_title,
    page_icon="🏙️",
    layout="wide",
)

apply_compact_academic_style()

st.title(settings.app_title)
st.write(
    "Este es el arranque técnico inicial del MVP. "
    "Desde aquí se organiza la navegación principal del sistema."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Estado del proyecto")
    st.markdown(
        """
        - Flujo real de uso definido
        - Rúbrica y evaluación estructuradas
        - Capa relacional documentada
        - Arranque técnico en proceso
        """
    )

with col2:
    st.subheader("Conexión con Supabase")
    if settings.has_supabase_credentials:
        st.success("Credenciales detectadas. La app está lista para probar conexión.")
    else:
        st.warning("No se detectaron credenciales. Revise el archivo .env.")

st.info(
    "Siguiente paso: completar las páginas base y conectar los servicios "
    "con la base de datos."
)
