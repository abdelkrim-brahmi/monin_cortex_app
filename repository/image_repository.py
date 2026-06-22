"""Couche Repository — images produits (table IMAGES).

Lien : IMAGES.PRODUCT_ID = SILVER_PRODUIT.EAN. Plusieurs images par produit,
ordonnées par POSITION (1 = image principale).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import T_IMAGES

CACHE_TTL = 600

# Sous-requête réutilisable : 1 image principale (POSITION mini) par produit.
MAIN_IMAGE_SUBQUERY = f"""(
    SELECT TO_VARCHAR(product_id) AS ean, image_url, alt
    FROM {T_IMAGES}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY position NULLS LAST) = 1
)"""


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_main_image_map(_session) -> dict:
    """Dictionnaire ean -> {url, alt} de l'image principale (lookup rapide)."""
    df = _session.sql(
        f"""
        SELECT TO_VARCHAR(product_id) AS ean, image_url, alt
        FROM {T_IMAGES}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY position NULLS LAST) = 1
        """
    ).to_pandas()
    return {r.EAN: {"url": r.IMAGE_URL, "alt": r.ALT or ""} for r in df.itertuples()}


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_images_for_ean(_session, ean) -> pd.DataFrame:
    """Toutes les images d'un produit (galerie), ordonnées par position."""
    return _session.sql(
        f"""
        SELECT image_url, alt, position
        FROM {T_IMAGES}
        WHERE TO_VARCHAR(product_id) = ?
        ORDER BY position NULLS LAST
        """,
        params=[str(ean)],
    ).to_pandas()


def image_url(image_map: dict, ean, placeholder: str) -> str:
    """URL de l'image principale d'un produit, sinon placeholder."""
    entry = image_map.get(str(ean))
    return entry["url"] if entry and entry.get("url") else placeholder
