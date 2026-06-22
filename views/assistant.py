"""Page 3 — Assistant IA conversationnel (Cortex Analyst).

L'utilisateur pose des questions en langage naturel ; Cortex Analyst génère le
SQL (gouverné par le semantic model), l'app l'exécute et Cortex Complete fournit
une explication métier. SQL + Résultat + Explication sont affichés.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services import cortex_analyst
from services.cortex_complete import complete
from prompts.templates import prompt_explication_resultat
from utils import ui, state

KEY_HISTORY = "assistant_history"

EXEMPLES = [
    "Quels sont les produits les plus à risque ?",
    "Quels importateurs ont la meilleure rotation ?",
    "Quels produits auront un manque de stock le mois prochain ?",
    "Quels produits sont surstockés ?",
    "Quel est le top 10 des risques ?",
    "Compare les prévisions aux ventes réelles",
    "Quels produits doivent être promus ?",
]


def render(session) -> None:
    ui.hero("🤖 Assistant IA",
            "Posez vos questions en langage naturel — Cortex Analyst génère le SQL, l'exécute et l'explique")

    history = st.session_state.setdefault(KEY_HISTORY, [])

    # Questions suggérées.
    with st.expander("💡 Questions suggérées", expanded=not history):
        cols = st.columns(2)
        for i, ex in enumerate(EXEMPLES):
            if cols[i % 2].button(ex, key=f"ex_{i}", use_container_width=True):
                _handle(session, ex, history)
                st.rerun()

    # Historique de conversation.
    for turn in history:
        with st.chat_message(turn["role"]):
            if turn["role"] == "user":
                st.markdown(turn["content"])
            else:
                _render_answer(turn["content"])

    # Question préremplie (scénario de démo).
    prefill = st.session_state.pop(state.KEY_CHAT_PREFILL, None)

    question = st.chat_input("Posez votre question…")
    if prefill and not question:
        question = prefill
    if question:
        _handle(session, question, history)
        st.rerun()


def _handle(session, question: str, history: list) -> None:
    history.append({"role": "user", "content": question})
    with st.spinner("Cortex Analyst génère et exécute la requête…"):
        # Historique texte pour le contexte multi-tours.
        ctx = [{"role": t["role"], "content": t["content"] if isinstance(t["content"], str)
                else t["content"].get("texte", "")} for t in history[:-1]]
        answer = cortex_analyst.ask_analyst(session, question, ctx)

        explication = answer.texte
        if answer.dataframe is not None and not answer.erreur:
            apercu = answer.dataframe.head(10).to_csv(index=False)
            explication = complete(
                session, prompt_explication_resultat(question, answer.sql, apercu),
                model=state.get_model())

        history.append({"role": "assistant", "content": {
            "texte": explication, "sql": answer.sql,
            "df": answer.dataframe, "erreur": answer.erreur,
            "suggestions": answer.suggestions,
        }})


def _render_answer(c: dict) -> None:
    if c.get("erreur"):
        st.error(c["erreur"])
    if c.get("texte"):
        st.markdown(c["texte"])

    df = c.get("df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        tab_res, tab_sql = st.tabs(["📊 Résultat", "🧾 SQL généré"])
        with tab_res:
            st.dataframe(df, use_container_width=True, hide_index=True)
            _auto_chart(df)
        with tab_sql:
            st.code(c.get("sql", ""), language="sql")
    elif c.get("sql"):
        st.code(c["sql"], language="sql")

    for s in c.get("suggestions", [])[:3]:
        st.caption(f"↳ suggestion : _{s}_")


def _auto_chart(df: pd.DataFrame) -> None:
    """Trace un graphique simple si la forme du résultat s'y prête."""
    num = df.select_dtypes("number").columns.tolist()
    cat = [c for c in df.columns if c not in num]
    if len(df) > 1 and num and cat:
        import plotly.express as px
        from config import COLOR_PRIMARY

        d = df.head(15)
        fig = px.bar(d, x=num[0], y=cat[0], orientation="h")
        fig.update_traces(marker_color=COLOR_PRIMARY)
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                          plot_bgcolor="white", yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
