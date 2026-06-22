"""Service Cortex Complete — génération de texte (LLM).

Appel via la fonction SQL ``SNOWFLAKE.CORTEX.COMPLETE`` pour une portabilité
maximale (fonctionne en SiS comme en local, sans dépendance au package
``snowflake.cortex``). Le prompt est passé en bind param (pas de concaténation).
"""
from __future__ import annotations

from config import DEFAULT_MODEL


def complete(session, prompt: str, model: str | None = None) -> str:
    """Génère une complétion texte. Renvoie un message d'erreur lisible en cas d'échec."""
    model = model or DEFAULT_MODEL
    try:
        row = session.sql(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS R",
            params=[model, prompt],
        ).collect()
        return (row[0]["R"] or "").strip()
    except Exception as e:  # noqa: BLE001
        return _format_error(model, e)


def complete_with_options(session, prompt: str, model: str | None = None,
                          temperature: float = 0.2, max_tokens: int = 1200) -> str:
    """Variante avec options (température basse pour des réponses factuelles)."""
    model = model or DEFAULT_MODEL
    try:
        row = session.sql(
            """
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                ?,
                [ {'role': 'user', 'content': ?} ],
                {'temperature': ?, 'max_tokens': ?}
            ):choices[0].messages::string AS R
            """,
            params=[model, prompt, temperature, max_tokens],
        ).collect()
        return (row[0]["R"] or "").strip()
    except Exception:  # noqa: BLE001 — repli sur la signature simple.
        return complete(session, prompt, model)


def _format_error(model: str, e: Exception) -> str:
    msg = str(e)
    hint = ""
    if "unknown model" in msg.lower() or "not available" in msg.lower():
        hint = (
            f"\n\n> ℹ️ Le modèle « {model} » n'est peut-être pas activé dans votre "
            "région. Essayez un autre modèle dans le sélecteur, ou activez la "
            "*cross-region inference* (ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION')."
        )
    return f"⚠️ Cortex Complete indisponible : {msg}{hint}"
