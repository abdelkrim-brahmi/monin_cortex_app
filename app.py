"""MONIN · Conseil Stock Intelligent — application de démonstration Cortex.

Point d'entrée Streamlit (Streamlit in Snowflake). Routeur de navigation,
sélecteurs globaux (importateur, modèle Cortex) et scénario de démonstration.

Architecture :
    app.py            → routeur + sélecteurs globaux
    views/            → une page = une fonction render(session)
    services/         → Cortex Complete / Analyst / Search + simulation
    repository/       → TOUT le SQL (rien dans les pages)
    models/ prompts/ utils/ config.py
"""
from __future__ import annotations

import streamlit as st

import config
from repository.connection import get_session, is_in_snowflake
from repository import stock_repository as repo
from utils import ui, state
from views import dashboard, simulation, assistant, recommandations, exploration_sql

st.set_page_config(page_title=config.APP_TITLE, page_icon="❄️", layout="wide")

PAGES = {
    "Dashboard": ("📊", dashboard.render),
    "Simulation": ("🧪", simulation.render),
    "Assistant IA": ("🤖", assistant.render),
    "Recommandations IA": ("🧭", recommandations.render),
    "Exploration SQL": ("🛠️", exploration_sql.render),
}


def _sidebar(session) -> str:
    with st.sidebar:
        st.image(config.LOGO_MONIN, use_container_width=True)
        st.markdown("<div style='text-align:center;color:#9FB3C8;font-size:.8rem;"
                    "margin:-.3rem 0 .6rem'>× Snowflake Cortex AI</div>",
                    unsafe_allow_html=True)

        # --- Sélection de l'importateur (globale) ---
        importateurs = repo.get_importateurs(session)
        labels = [f"{r.NOM} — {r.ZONE}" for r in importateurs.itertuples()]
        ids = importateurs["IMPORTATEUR_ID"].tolist()

        current_id = st.session_state.get(state.KEY_IMPORTATEUR_ID)
        default_idx = ids.index(current_id) if current_id in ids else 0
        imp_token = st.session_state.get("imp_token", 0)

        sel = st.selectbox("🏢 Importateur", range(len(ids)),
                           index=default_idx if ids else 0,
                           format_func=lambda i: labels[i], key=f"sb_importateur_{imp_token}")
        if ids:
            state.set_importateur(ids[sel], labels[sel])

        st.divider()

        # --- Navigation ---
        names = list(PAGES.keys())
        current_nav = st.session_state.get(state.KEY_NAV, "Dashboard")
        nav_idx = names.index(current_nav) if current_nav in names else 0
        nav_token = st.session_state.get("nav_token", 0)
        page = st.radio("Navigation", names, index=nav_idx,
                        format_func=lambda n: f"{PAGES[n][0]}  {n}",
                        key=f"nav_{nav_token}", label_visibility="collapsed")
        st.session_state[state.KEY_NAV] = page

        st.divider()

        # --- Modèle Cortex ---
        st.session_state[state.KEY_MODEL] = st.selectbox(
            "🧠 Modèle Cortex", config.AVAILABLE_MODELS,
            index=config.AVAILABLE_MODELS.index(state.get_model())
            if state.get_model() in config.AVAILABLE_MODELS else 0)

        # --- Scénario de démonstration (bonus) ---
        st.divider()
        if st.button("🎬 Scénario de démonstration", use_container_width=True, type="primary"):
            _lancer_demo(session)

        mode = "Streamlit in Snowflake" if is_in_snowflake() else "Mode local (Snowpark)"
        st.caption(f"🔌 {mode}")

        # --- Signature TeamWork ---
        st.divider()
        st.markdown("<div style='text-align:center;color:#9FB3C8;font-size:.72rem;"
                    "margin-bottom:.3rem'>Réalisé par</div>", unsafe_allow_html=True)
        lc, cc, rc = st.columns([1, 3, 1])
        with cc:
            st.image(config.LOGO_TEAMWORK, use_container_width=True)

    return page


def _lancer_demo(session) -> None:
    """Prépare le scénario : importateur le plus à risque + flag d'auto-run."""
    top = repo.get_importateur_top_risque(session)
    state.force_importateur(top["IMPORTATEUR_ID"], f"{top['NOM']} — {top['ZONE']}")
    st.session_state[simulation.KEY_DEMO] = True
    state.goto("Simulation")
    st.rerun()


def main() -> None:
    ui.inject_css()
    session = get_session()
    page = _sidebar(session)
    PAGES[page][1](session)


if __name__ == "__main__":
    main()
