"""Design system — CSS Snowflake, composants visuels réutilisables.

Palette bleu / blanc, cartes KPI, badges, en-têtes de section. Toute la
présentation visuelle transverse est centralisée ici.
"""
from __future__ import annotations

import streamlit as st

from config import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_NAVY,
    COLOR_RISK,
    COLOR_OPPORTUNITY,
    COLOR_BG,
)


def inject_css() -> None:
    """Injecte le thème global (une seule fois par session de rendu)."""
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {COLOR_BG}; }}
        .block-container {{ padding-top: 1.6rem; max-width: 1280px; }}

        /* En-tête héro */
        .monin-hero {{
            background: linear-gradient(120deg, {COLOR_PRIMARY_DARK} 0%, {COLOR_PRIMARY} 100%);
            color: white; padding: 1.4rem 1.8rem; border-radius: 16px;
            margin-bottom: 1.4rem; box-shadow: 0 8px 24px rgba(17,86,127,.22);
        }}
        .monin-hero h1 {{ margin: 0; font-size: 1.55rem; font-weight: 700; letter-spacing:-.3px; }}
        .monin-hero p  {{ margin: .3rem 0 0; opacity: .92; font-size: .95rem; }}

        /* Cartes KPI */
        .kpi-card {{
            background: white; border-radius: 14px; padding: 1.05rem 1.15rem;
            border: 1px solid #E6EEF7; box-shadow: 0 2px 10px rgba(27,42,74,.05);
            height: 100%; transition: transform .15s ease, box-shadow .15s ease;
        }}
        .kpi-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 22px rgba(27,42,74,.12); }}
        .kpi-label {{ color:#6B7C93; font-size:.78rem; font-weight:600; text-transform:uppercase; letter-spacing:.4px; }}
        .kpi-value {{ color:{COLOR_NAVY}; font-size:1.7rem; font-weight:750; line-height:1.1; margin-top:.25rem; }}
        .kpi-icon  {{ font-size:1.15rem; float:right; opacity:.85; }}
        .kpi-sub   {{ color:#90A0B5; font-size:.78rem; margin-top:.2rem; }}

        /* Cartes avant / après */
        .ba-card {{ background:white; border-radius:14px; padding:1rem 1.2rem; border:1px solid #E6EEF7; text-align:center; }}
        .ba-before {{ color:#90A0B5; font-size:1.5rem; font-weight:700; }}
        .ba-arrow {{ color:{COLOR_PRIMARY}; font-size:1.3rem; }}
        .ba-after-good {{ color:{COLOR_OPPORTUNITY}; font-size:1.9rem; font-weight:800; }}
        .ba-after-bad  {{ color:{COLOR_RISK}; font-size:1.9rem; font-weight:800; }}
        .ba-after-neutral {{ color:{COLOR_NAVY}; font-size:1.9rem; font-weight:800; }}

        /* Encart IA */
        .ai-box {{
            background: linear-gradient(180deg,#FFFFFF,#F2F9FF);
            border-left: 4px solid {COLOR_PRIMARY}; border-radius: 10px;
            padding: 1.1rem 1.3rem; margin: .6rem 0; box-shadow:0 2px 10px rgba(27,42,74,.06);
        }}
        .doc-chip {{
            display:inline-block; background:{COLOR_PRIMARY}14; color:{COLOR_PRIMARY_DARK};
            border:1px solid {COLOR_PRIMARY}33; border-radius:8px; padding:.45rem .7rem;
            margin:.25rem .35rem .25rem 0; font-size:.82rem;
        }}
        section[data-testid="stSidebar"] {{ background: {COLOR_NAVY}; }}
        section[data-testid="stSidebar"] * {{ color: #E8EEF6; }}
        .stButton>button {{ border-radius:10px; font-weight:600; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='monin-hero'><h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, icon: str = "", sub: str = "", color: str | None = None) -> str:
    """Retourne le HTML d'une carte KPI (à placer dans une colonne)."""
    value_style = f"color:{color}" if color else ""
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='kpi-card'><span class='kpi-icon'>{icon}</span>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value' style='{value_style}'>{value}</div>{sub_html}</div>"
    )


def render_kpis(cards: list[str]) -> None:
    """Affiche une rangée de cartes KPI responsives."""
    cols = st.columns(len(cards))
    for col, html in zip(cols, cards):
        col.markdown(html, unsafe_allow_html=True)


def ai_box(markdown_text: str, title: str = "💡 Analyse IA") -> None:
    # st.container(border=True) garantit un rendu markdown fiable du texte IA
    # (le markdown imbriqué dans un <div> HTML n'est pas toujours interprété).
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.markdown(markdown_text)


def section(title: str, emoji: str = "") -> None:
    st.markdown(f"#### {emoji} {title}")
