"""Service Cortex Complete — génération de texte (LLM).

Appel via la fonction SQL ``SNOWFLAKE.CORTEX.COMPLETE`` pour une portabilité
maximale (fonctionne en SiS comme en local, sans dépendance au package
``snowflake.cortex``). Le prompt est passé en bind param (pas de concaténation).

Résilience régionale : si le modèle choisi est indisponible dans la région du
compte, on bascule automatiquement sur les modèles de repli (config.FALLBACK_MODELS).
"""
from __future__ import annotations

from config import DEFAULT_MODEL, FALLBACK_MODELS


def complete(session, prompt: str, model: str | None = None) -> str:
    """Génère une complétion texte avec repli automatique de modèle.

    Renvoie un message d'erreur lisible si aucun modèle ne répond.
    """
    model = model or DEFAULT_MODEL
    # Modèle demandé d'abord, puis les replis (sans doublon).
    candidates = [model] + [m for m in FALLBACK_MODELS if m != model]

    last_err: Exception | None = None
    for i, mdl in enumerate(candidates):
        try:
            row = session.sql(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS R",
                params=[mdl, prompt],
            ).collect()
            text = (row[0]["R"] or "").strip()
            # Préfixe discret si l'on a dû basculer sur un modèle de repli.
            if i > 0 and text:
                text = f"_(modèle « {model} » indisponible — réponse générée par « {mdl} »)_\n\n{text}"
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            if not _is_unavailable(e):
                # Erreur non liée à la disponibilité : inutile d'insister.
                break
    return _format_error(model, last_err)


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
    except Exception:  # noqa: BLE001 — repli sur la signature simple + fallback modèle.
        return complete(session, prompt, model)


def _is_unavailable(e: Exception) -> bool:
    msg = str(e).lower()
    return "unavailable" in msg or "unknown model" in msg or "not available" in msg \
        or "not enabled" in msg or "400" in msg


def _format_error(model: str, e: Exception | None) -> str:
    msg = str(e) if e else "erreur inconnue"
    hint = ""
    if e and _is_unavailable(e):
        hint = (
            f"\n\n> ℹ️ Le modèle « {model} » et les modèles de repli ne sont pas "
            "activés dans la région de ce compte. Pour utiliser Claude, activez "
            "l'inférence cross-region en ACCOUNTADMIN :\n"
            "> ```sql\n> ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';\n> ```"
        )
    return f"⚠️ Cortex Complete indisponible : {msg}{hint}"
