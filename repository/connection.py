"""Gestion de la session Snowpark — session unique partagée.

En production (Streamlit in Snowflake) on récupère la session active via
``get_active_session()``. En développement local, on retombe sur une
``Session`` construite depuis ``connections.toml`` / variables d'environnement,
ce qui rend le module exécutable hors SiS sans modification de code.
"""
from __future__ import annotations

import streamlit as st


@st.cache_resource(show_spinner=False)
def get_session():
    """Retourne la session Snowpark unique (mise en cache pour toute l'app)."""
    # 1) Streamlit in Snowflake : session déjà disponible.
    try:
        from snowflake.snowpark.context import get_active_session

        return get_active_session()
    except Exception:  # noqa: BLE001 — pas en SiS, on tente le mode local.
        pass

    # 2) Fallback local : connexion nommée "monin" dans ~/.snowflake/connections.toml
    #    ou variables SNOWFLAKE_* . Permet `streamlit run app.py` en local.
    from snowflake.snowpark import Session

    try:
        return Session.builder.config("connection_name", "monin").create()
    except Exception:  # noqa: BLE001
        import os

        params = {
            "account": os.environ.get("SNOWFLAKE_ACCOUNT", "A3857344721571-TEAMWORKCORP_PARTNER"),
            "user": os.environ.get("SNOWFLAKE_USER", "ABRAHMI"),
            "authenticator": os.environ.get("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
            "role": os.environ.get("SNOWFLAKE_ROLE", "SNOWFLAKE_INTELLIGENCE_ADMIN"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.environ.get("SNOWFLAKE_DATABASE", "MONIN"),
            "schema": os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        }
        pwd = os.environ.get("SNOWFLAKE_PASSWORD")
        if pwd:
            params["password"] = pwd
            params.pop("authenticator", None)
        return Session.builder.configs(params).create()


def is_in_snowflake() -> bool:
    """True si l'on s'exécute dans Streamlit in Snowflake (module _snowflake présent)."""
    try:
        import _snowflake  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False
