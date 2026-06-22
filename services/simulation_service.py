"""Service de simulation — cœur de la démonstration (Page 2).

Orchestration : capture KPI avant → MERGE de la vente → relecture KPI après
(la vue GOLD se recalcule automatiquement) → explication via Cortex Complete.
"""
from __future__ import annotations

from typing import Optional

from models.entities import KpiSnapshot, SimulationResult
from prompts.templates import prompt_explication_simulation
from repository import stock_repository as repo
from services.cortex_complete import complete


def _to_snapshot(row: Optional[dict]) -> KpiSnapshot:
    if not row:
        return KpiSnapshot()
    return KpiSnapshot(
        stock_actuel=row.get("STOCK_ACTUEL"),
        ventes_moy_mensuelles=row.get("VENTES_MOY_MENSUELLES"),
        couverture_jours=row.get("COUVERTURE_JOURS"),
        rotation_annuelle=row.get("ROTATION_ANNUELLE"),
        ecart_prevision_reel_pct=row.get("ECART_PREVISION_REEL_PCT"),
        score_risque=row.get("SCORE_RISQUE_IMMOBILISATION"),
        statut=row.get("STATUT"),
    )


def simuler_vente(session, importateur_id, ean: str, mois: str, nouvelle_quantite: float,
                  model: str | None = None, generer_explication: bool = True) -> SimulationResult:
    """Exécute la simulation complète et renvoie le résultat avant/après."""
    # 1. Situation AVANT.
    avant_row = repo.get_conseil_produit(session, importateur_id, ean)
    avant = _to_snapshot(avant_row)
    libelle = (avant_row or {}).get("LIBELLE", ean)

    # Quantité existante pour ce mois (pour l'affichage avant/après).
    mois_df = repo.get_mois_ventes(session, importateur_id, ean)
    q_avant = None
    if not mois_df.empty:
        match = mois_df[mois_df["MOIS"].astype(str) == str(mois)]
        if not match.empty:
            q_avant = float(match.iloc[0]["QUANTITE"])

    # 2. Écriture (insert ou update) + 3. recalcul automatique de la vue GOLD.
    repo.upsert_vente(session, importateur_id, ean, mois, nouvelle_quantite)

    # 4. Situation APRÈS.
    apres = _to_snapshot(repo.get_conseil_produit(session, importateur_id, ean))

    result = SimulationResult(
        importateur_id=str(importateur_id), ean=ean, libelle=libelle, mois=str(mois),
        quantite_avant=q_avant, quantite_apres=float(nouvelle_quantite),
        avant=avant, apres=apres,
    )

    # 5. Explication métier générée par Cortex Complete.
    if generer_explication:
        result.explication = complete(
            session,
            prompt_explication_simulation({
                "libelle": libelle, "ean": ean, "mois": mois,
                "quantite_avant": q_avant if q_avant is not None else "0 (aucune vente)",
                "quantite_apres": nouvelle_quantite,
                "couv_avant": _fmt(avant.couverture_jours), "couv_apres": _fmt(apres.couverture_jours),
                "rota_avant": _fmt(avant.rotation_annuelle), "rota_apres": _fmt(apres.rotation_annuelle),
                "score_avant": avant.score_100, "score_apres": apres.score_100,
                "statut_avant": avant.statut, "statut_apres": apres.statut,
            }),
            model=model,
        )
    return result


def _fmt(v) -> str:
    return "N/A" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))
