"""Service Cortex Search — recherche sémantique dans les documents marketing.

Interroge le service de recherche créé sur SILVER_MARKETING via la fonction
``SNOWFLAKE.CORTEX.SEARCH_PREVIEW`` (SQL), robuste et sans dépendance externe.
Repli automatique sur un filtre LIKE si le service n'est pas encore déployé.
"""
from __future__ import annotations

import json

from config import (
    CORTEX_SEARCH_SERVICE,
    SEARCH_TEXT_COLUMN,
    SEARCH_ATTR_COLUMNS,
    T_MARKETING,
)
from models.entities import MarketingDoc


def search_documents(session, query: str, limit: int = 4,
                     zone: str | None = None, gamme: str | None = None) -> list[MarketingDoc]:
    """Retourne les documents marketing les plus pertinents pour la requête."""
    columns = [SEARCH_TEXT_COLUMN] + SEARCH_ATTR_COLUMNS
    payload = {"query": query, "columns": columns, "limit": limit}

    # Filtre optionnel par attribut (zone / gamme) — affine la pertinence.
    filters = []
    if zone:
        filters.append({"@eq": {"ZONE": zone}})
    if gamme:
        filters.append({"@eq": {"GAMME": gamme}})
    if filters:
        payload["filter"] = {"@and": filters} if len(filters) > 1 else filters[0]

    try:
        row = session.sql(
            "SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(?, ?) AS R",
            params=[CORTEX_SEARCH_SERVICE, json.dumps(payload)],
        ).collect()
        results = json.loads(row[0]["R"]).get("results", [])
        return [_to_doc(r) for r in results]
    except Exception:  # noqa: BLE001 — service absent : repli lexical.
        return _fallback_like(session, query, limit)


def _to_doc(r: dict) -> MarketingDoc:
    return MarketingDoc(
        doc_id=r.get("DOC_ID", ""),
        titre=r.get("TITRE", ""),
        zone=r.get("ZONE", ""),
        gamme=r.get("GAMME", ""),
        date_pub=str(r.get("DATE_PUB", "")),
        contenu=r.get(SEARCH_TEXT_COLUMN, ""),
        score=float(r.get("@score", r.get("score", 0.0)) or 0.0),
    )


def _fallback_like(session, query: str, limit: int) -> list[MarketingDoc]:
    """Repli sans Cortex Search : recherche par mots-clés (mode dégradé)."""
    terms = [t for t in query.lower().split() if len(t) > 3][:4]
    if not terms:
        terms = [query.lower()]
    like = " OR ".join(["LOWER(contenu || ' ' || titre) LIKE ?" for _ in terms])
    params = [f"%{t}%" for t in terms] + [limit]
    try:
        df = session.sql(
            f"""
            SELECT doc_id, titre, zone, gamme, date_pub, contenu
            FROM {T_MARKETING}
            WHERE {like}
            LIMIT ?
            """,
            params=params,
        ).to_pandas()
    except Exception:  # noqa: BLE001
        return []
    return [
        MarketingDoc(
            doc_id=r.DOC_ID, titre=r.TITRE, zone=r.ZONE, gamme=r.GAMME,
            date_pub=str(r.DATE_PUB), contenu=r.CONTENU, score=0.0,
        )
        for r in df.itertuples()
    ]
