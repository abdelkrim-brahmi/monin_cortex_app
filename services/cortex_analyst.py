"""Service Cortex Analyst — texte → SQL gouverné par un semantic model.

En Streamlit in Snowflake, on appelle l'API REST interne via
``_snowflake.send_snow_api_request`` (pas de gestion de token). Le semantic
model YAML doit être déposé sur le stage défini dans config (sql/01_*.sql).

Si Cortex Analyst n'est pas disponible (hors SiS, model absent), on bascule sur
un mode dégradé : génération du SQL par Cortex Complete à partir du schéma.
"""
from __future__ import annotations

import json

import pandas as pd

from config import (
    SEMANTIC_MODEL_PATH,
    ANALYST_ENDPOINT,
    ANALYST_TIMEOUT_MS,
    V_GOLD,
)
from models.entities import AnalystAnswer
from prompts.templates import prompt_sql_fallback
from services.cortex_complete import complete

SCHEMA_HINT = f"""
- {V_GOLD} (vue principale) : importateur_id, importateur, zone, commercial,
  ean, libelle, gamme, statut_produit, mois_courant, stock_actuel,
  ventes_moy_mensuelles, couverture_jours, rotation_annuelle,
  prevision_mois_suivant, reel_mois_courant, prevu_mois_courant,
  ecart_prevision_reel_pct, score_risque_immobilisation, statut
  (statut ∈ 'à risque' | 'opportunité' | 'normal')
"""


def ask_analyst(session, question: str, history: list | None = None) -> AnalystAnswer:
    """Pose une question. Renvoie texte + SQL + DataFrame."""
    answer = _call_analyst_rest(session, question, history or [])
    if answer is None:
        answer = _fallback_complete(session, question)

    # Exécution du SQL généré pour récupérer le résultat tabulaire.
    if answer.sql and not answer.erreur:
        try:
            answer.dataframe = session.sql(answer.sql).to_pandas()
        except Exception as e:  # noqa: BLE001
            answer.erreur = f"Erreur d'exécution du SQL généré : {e}"
    return answer


def _call_analyst_rest(session, question: str, history: list):
    """Appel REST Cortex Analyst (SiS uniquement). Renvoie None si indisponible."""
    try:
        import _snowflake
    except Exception:  # noqa: BLE001 — pas en SiS.
        return None

    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": [{"type": "text", "text": h["content"]}]})
    messages.append({"role": "user", "content": [{"type": "text", "text": question}]})

    body = {"messages": messages, "semantic_model_file": SEMANTIC_MODEL_PATH}

    try:
        resp = _snowflake.send_snow_api_request(
            "POST", ANALYST_ENDPOINT, {}, {}, body, {}, ANALYST_TIMEOUT_MS,
        )
        if resp["status"] != 200:
            return AnalystAnswer(erreur=f"Cortex Analyst a renvoyé le statut {resp['status']} : {resp.get('content', '')[:300]}")
        content = json.loads(resp["content"])
        return _parse_analyst_message(content)
    except Exception as e:  # noqa: BLE001
        return AnalystAnswer(erreur=f"Appel Cortex Analyst échoué : {e}")


def _parse_analyst_message(content: dict) -> AnalystAnswer:
    ans = AnalystAnswer()
    msg = content.get("message", {})
    for item in msg.get("content", []):
        if item.get("type") == "text":
            ans.texte += item.get("text", "")
        elif item.get("type") == "sql":
            ans.sql = item.get("statement", "").strip()
        elif item.get("type") == "suggestions":
            ans.suggestions = item.get("suggestions", [])
    return ans


def _fallback_complete(session, question: str) -> AnalystAnswer:
    """Mode dégradé : Cortex Complete génère le SQL depuis le schéma."""
    raw = complete(session, prompt_sql_fallback(question, SCHEMA_HINT))
    sql = _clean_sql(raw)
    if not sql.lower().lstrip().startswith(("select", "with")):
        return AnalystAnswer(
            texte="Cortex Analyst n'est pas disponible et la génération de repli "
                  "n'a pas produit de SQL exploitable.",
            erreur=raw[:300],
        )
    return AnalystAnswer(
        texte="_(Cortex Analyst indisponible — SQL généré via Cortex Complete.)_",
        sql=sql,
    )


def _clean_sql(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lower().startswith("sql"):
            s = s[3:]
    return s.strip().rstrip(";").strip()
