"""Estilos visuales compartidos para la interfaz Streamlit."""

from __future__ import annotations

import streamlit as st


def apply_compact_academic_style() -> None:
    """Aplica una escala visual sobria y compacta a una pantalla."""
    st.markdown(
        """
        <style>
        .stApp {
            font-size: 0.87rem;
        }

        .stApp h1 {
            font-size: 1.72rem;
            line-height: 1.18;
            margin-bottom: 0.32rem;
        }

        .stApp h2 {
            font-size: 1.14rem;
            line-height: 1.26;
            margin-top: 0.42rem;
            margin-bottom: 0.24rem;
        }

        .stApp h3 {
            font-size: 0.98rem;
            line-height: 1.3;
            margin-top: 0.32rem;
            margin-bottom: 0.2rem;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 1.35rem;
        }

        hr {
            margin: 0.48rem 0;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.68rem;
            line-height: 1.15;
        }

        [data-testid="stMetricValue"] {
            font-size: 0.98rem;
            line-height: 1.12;
        }

        [data-testid="stMetric"] {
            padding: 0.02rem 0;
        }

        [data-testid="stCaptionContainer"],
        .stMarkdown p,
        .stInfo,
        .stWarning,
        .stSuccess {
            font-size: 0.81rem;
            line-height: 1.35;
        }

        .stMarkdown ul {
            margin-top: 0.18rem;
            margin-bottom: 0.42rem;
        }

        .stMarkdown li {
            margin-bottom: 0.12rem;
            line-height: 1.34;
        }

        div[data-testid="stAlert"] {
            padding: 0.32rem 0.58rem;
            margin: 0.24rem 0;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.25rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.5rem 0.66rem;
            margin-bottom: 0.26rem;
        }

        [data-testid="stWidgetLabel"] {
            font-size: 0.82rem;
            line-height: 1.25;
        }

        [data-baseweb="tab-list"] {
            gap: 0.18rem;
        }

        [data-baseweb="tab"] {
            font-size: 0.82rem;
            padding-top: 0.34rem;
            padding-bottom: 0.34rem;
        }

        div[data-testid="stExpander"] details {
            margin-top: 0.12rem;
            margin-bottom: 0.18rem;
        }

        div[data-testid="stExpander"] summary p {
            font-size: 0.84rem;
            font-weight: 600;
        }

        .stButton button,
        .stDownloadButton button {
            font-size: 0.82rem;
            padding-top: 0.3rem;
            padding-bottom: 0.3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
