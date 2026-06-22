"""Couche Repository — TOUT le SQL de l'application est centralisé ici.

Règle d'or : aucune requête SQL ne doit apparaître dans les pages Streamlit.
Les fonctions de lecture sont mises en cache (``st.cache_data``) ; le premier
argument ``_session`` est préfixé d'un underscore pour être ignoré par le
hachage du cache (un objet Session n'est pas hachable).

Les fonctions d'écriture (MERGE) invalident le cache de lecture.
"""
from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import streamlit as st

from config import (
    T_VENTES,
    T_STOCK,
    T_IMPORTATEUR,
    V_GOLD,
    T_MARKETING,
    DATABASE,
    SCHEMA,
)

CACHE_TTL = 300  # secondes


# --------------------------------------------------------------------------- #
# Helpers internes
# --------------------------------------------------------------------------- #
def _df(_session, sql: str, params: Optional[list] = None) -> pd.DataFrame:
    """Exécute une requête et renvoie un DataFrame (colonnes en MAJUSCULES)."""
    return _session.sql(sql, params=params).to_pandas()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def has_ca_column(_session) -> bool:
    """Vrai si SILVER_VENTES expose une colonne CA (chiffre d'affaires).

    Permet d'afficher un CA réel ; sinon l'app retombe proprement sur le volume.
    """
    cols = _df(
        _session,
        f"""
        SELECT column_name
        FROM {DATABASE}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema = '{SCHEMA}' AND table_name = 'SILVER_VENTES'
        """,
    )
    return "CA" in {c.upper() for c in cols["COLUMN_NAME"]}


# --------------------------------------------------------------------------- #
# Dimensions / sélecteurs
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_importateurs(_session) -> pd.DataFrame:
    return _df(
        _session,
        f"""
        SELECT importateur_id, nom, zone, commercial
        FROM {T_IMPORTATEUR}
        ORDER BY nom
        """,
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_produits_importateur(_session, importateur_id) -> pd.DataFrame:
    """Produits référencés pour un importateur (avec libellé), depuis la GOLD."""
    return _df(
        _session,
        f"""
        SELECT DISTINCT ean, libelle, gamme
        FROM {V_GOLD}
        WHERE importateur_id = ?
        ORDER BY libelle
        """,
        params=[importateur_id],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_mois_ventes(_session, importateur_id, ean) -> pd.DataFrame:
    """Mois de vente disponibles pour un couple importateur/produit."""
    return _df(
        _session,
        f"""
        SELECT mois, quantite
        FROM {T_VENTES}
        WHERE importateur_id = ? AND ean = ?
        ORDER BY mois DESC
        """,
        params=[importateur_id, ean],
    )


# --------------------------------------------------------------------------- #
# Dashboard (Page 1)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_conseil(_session, importateur_id) -> pd.DataFrame:
    """Table détaillée GOLD_CONSEIL_STOCK pour un importateur."""
    return _df(
        _session,
        f"""
        SELECT ean, libelle, gamme, statut_produit,
               stock_actuel, ventes_moy_mensuelles,
               couverture_jours, rotation_annuelle,
               prevision_mois_suivant, reel_mois_courant, prevu_mois_courant,
               ecart_prevision_reel_pct, score_risque_immobilisation, statut
        FROM {V_GOLD}
        WHERE importateur_id = ?
        ORDER BY score_risque_immobilisation DESC NULLS LAST
        """,
        params=[importateur_id],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_resume(_session, importateur_id) -> dict:
    """KPI agrégés d'en-tête pour le dashboard."""
    g = _df(
        _session,
        f"""
        SELECT
            COUNT(*)                                                  AS nb_produits,
            COALESCE(SUM(stock_actuel), 0)                            AS stock_total,
            COALESCE(SUM(prevision_mois_suivant), 0)                  AS prev_total,
            SUM(IFF(statut = 'à risque', 1, 0))                       AS nb_risque,
            SUM(IFF(statut = 'opportunité', 1, 0))                    AS nb_opportunite,
            AVG(couverture_jours)                                     AS couverture_moy,
            AVG(rotation_annuelle)                                    AS rotation_moy
        FROM {V_GOLD}
        WHERE importateur_id = ?
        """,
        params=[importateur_id],
    ).iloc[0].to_dict()

    # CA réel (colonne SILVER_VENTES.CA) sinon volume vendu — 12 derniers mois.
    is_revenue = has_ca_column(_session)
    metric = "SUM(ca)" if is_revenue else "SUM(quantite)"
    value = _df(
        _session,
        f"""
        SELECT COALESCE({metric}, 0) AS v
        FROM {T_VENTES}
        WHERE importateur_id = ?
          AND mois > DATEADD('month', -12, (SELECT MAX(mois) FROM {T_VENTES}))
        """,
        params=[importateur_id],
    ).iloc[0, 0]
    g["ca"] = float(value or 0)
    g["ca_is_revenue"] = is_revenue
    return g


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_ventes_mensuelles(_session, importateur_id) -> pd.DataFrame:
    return _df(
        _session,
        f"""
        SELECT mois, SUM(quantite) AS quantite
        FROM {T_VENTES}
        WHERE importateur_id = ?
        GROUP BY mois
        ORDER BY mois
        """,
        params=[importateur_id],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_stock_mensuel(_session, importateur_id) -> pd.DataFrame:
    return _df(
        _session,
        f"""
        SELECT mois, SUM(quantite_stock) AS quantite_stock
        FROM {T_STOCK}
        WHERE importateur_id = ?
        GROUP BY mois
        ORDER BY mois
        """,
        params=[importateur_id],
    )


# --------------------------------------------------------------------------- #
# Simulation (Page 2)
# --------------------------------------------------------------------------- #
def get_conseil_produit(_session, importateur_id, ean) -> Optional[dict]:
    """Ligne GOLD d'un produit (non caché : relu avant/après simulation)."""
    df = _df(
        _session,
        f"""
        SELECT libelle, stock_actuel, ventes_moy_mensuelles,
               couverture_jours, rotation_annuelle,
               ecart_prevision_reel_pct, score_risque_immobilisation, statut
        FROM {V_GOLD}
        WHERE importateur_id = ? AND ean = ?
        """,
        params=[importateur_id, ean],
    )
    return None if df.empty else df.iloc[0].to_dict()


def upsert_vente(_session, importateur_id, ean, mois: str, quantite: float) -> None:
    """Insère ou met à jour la quantité vendue (MERGE idempotent).

    ``mois`` au format 'YYYY-MM-DD'. Invalide ensuite le cache de lecture afin
    que la vue GOLD soit relue avec la nouvelle vente.
    """
    # On renseigne aussi le CA : prix unitaire moyen observé pour ce produit
    # × nouvelle quantité, afin que le CA du dashboard reste cohérent.
    q = float(quantite)
    _session.sql(
        f"""
        MERGE INTO {T_VENTES} t
        USING (
            SELECT ? AS importateur_id, ? AS ean, TO_DATE(?) AS mois, ?::FLOAT AS quantite,
                   ?::FLOAT * COALESCE((
                       SELECT AVG(ca / NULLIF(quantite, 0))
                       FROM {T_VENTES}
                       WHERE importateur_id = ? AND ean = ?
                         AND ca IS NOT NULL AND quantite > 0
                   ), 0) AS ca
        ) s
        ON t.importateur_id = s.importateur_id AND t.ean = s.ean AND t.mois = s.mois
        WHEN MATCHED THEN UPDATE SET t.quantite = s.quantite, t.ca = s.ca
        WHEN NOT MATCHED THEN INSERT (importateur_id, ean, mois, quantite, ca)
             VALUES (s.importateur_id, s.ean, s.mois, s.quantite, s.ca)
        """,
        params=[importateur_id, ean, mois, q, q, importateur_id, ean],
    ).collect()
    # La vue GOLD dépend de SILVER_VENTES : on purge les lectures mises en cache.
    st.cache_data.clear()


# --------------------------------------------------------------------------- #
# Scénario de démonstration (bonus)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_importateur_top_risque(_session) -> dict:
    """Importateur cumulant le plus de risque (pour le scénario auto)."""
    return _df(
        _session,
        f"""
        SELECT importateur_id, ANY_VALUE(importateur) AS nom, ANY_VALUE(zone) AS zone,
               COUNT_IF(statut = 'à risque') AS nb_risque,
               SUM(score_risque_immobilisation) AS risque_total
        FROM {V_GOLD}
        GROUP BY importateur_id
        ORDER BY nb_risque DESC, risque_total DESC NULLS LAST
        LIMIT 1
        """,
    ).iloc[0].to_dict()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_produit_top_risque(_session, importateur_id) -> dict:
    """Produit le plus à risque d'un importateur (pour le scénario auto)."""
    df = _df(
        _session,
        f"""
        SELECT ean, libelle, couverture_jours, score_risque_immobilisation,
               ventes_moy_mensuelles
        FROM {V_GOLD}
        WHERE importateur_id = ?
        ORDER BY score_risque_immobilisation DESC NULLS LAST
        LIMIT 1
        """,
        params=[importateur_id],
    )
    return {} if df.empty else df.iloc[0].to_dict()


# --------------------------------------------------------------------------- #
# Recommandations (Page 4)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_produits_a_risque(_session, importateur_id, limit: int = 15) -> pd.DataFrame:
    return _df(
        _session,
        f"""
        SELECT ean, libelle, gamme, zone, statut,
               couverture_jours, rotation_annuelle,
               score_risque_immobilisation, stock_actuel, ventes_moy_mensuelles
        FROM {V_GOLD}
        WHERE importateur_id = ?
        ORDER BY score_risque_immobilisation DESC NULLS LAST
        LIMIT ?
        """,
        params=[importateur_id, limit],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_marketing_apercu(_session) -> pd.DataFrame:
    return _df(
        _session,
        f"""
        SELECT doc_id, date_pub, titre, zone, gamme, contenu
        FROM {T_MARKETING}
        ORDER BY date_pub DESC
        """,
    )


# --------------------------------------------------------------------------- #
# Exploration SQL (Page 5)
# --------------------------------------------------------------------------- #
def run_sql(_session, sql: str) -> dict:
    """Exécute une requête libre et renvoie résultat, durée et plan d'exécution."""
    started = time.perf_counter()
    df = _session.sql(sql).to_pandas()
    elapsed = time.perf_counter() - started

    plan = ""
    try:
        plan_df = _session.sql(f"EXPLAIN USING TEXT {sql}").to_pandas()
        plan = "\n".join(str(v) for v in plan_df.iloc[:, 0].tolist())
    except Exception as e:  # noqa: BLE001 — EXPLAIN peut échouer (DDL, etc.)
        plan = f"(plan indisponible : {e})"

    return {"dataframe": df, "elapsed": elapsed, "plan": plan}
