"""Helpers d'état partagé entre les pages (st.session_state)."""
from __future__ import annotations

import streamlit as st

KEY_IMPORTATEUR_ID = "importateur_id"
KEY_IMPORTATEUR_LABEL = "importateur_label"
KEY_NAV = "nav_page"
KEY_CHAT_PREFILL = "chat_prefill"
KEY_LAST_SIM = "last_simulation"
KEY_MODEL = "cortex_model"


def get_importateur():
    return st.session_state.get(KEY_IMPORTATEUR_ID), st.session_state.get(KEY_IMPORTATEUR_LABEL)


def set_importateur(importateur_id, label) -> None:
    st.session_state[KEY_IMPORTATEUR_ID] = importateur_id
    st.session_state[KEY_IMPORTATEUR_LABEL] = label


def force_importateur(importateur_id, label) -> None:
    """Change l'importateur par programme (scénario démo) et force le rafraîchissement
    du sélecteur via un token de widget."""
    set_importateur(importateur_id, label)
    st.session_state["imp_token"] = st.session_state.get("imp_token", 0) + 1


def goto(page: str) -> None:
    """Navigation programmatique vers une page (utilisé par le scénario démo).

    Incrémente un token afin de recréer le widget radio et imposer la nouvelle
    page (un widget Streamlit conserve sinon son état interne)."""
    st.session_state[KEY_NAV] = page
    st.session_state["nav_token"] = st.session_state.get("nav_token", 0) + 1


def get_model() -> str:
    from config import DEFAULT_MODEL

    return st.session_state.get(KEY_MODEL, DEFAULT_MODEL)


def require_importateur() -> bool:
    """Garde-fou : affiche un message si aucun importateur n'est sélectionné."""
    imp_id, _ = get_importateur()
    if not imp_id:
        st.info("👈 Sélectionnez un importateur dans la barre latérale pour commencer.")
        return False
    return True
