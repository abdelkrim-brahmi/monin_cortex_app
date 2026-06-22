"""Modèles de domaine — structures typées échangées entre couches.

Volontairement légers : on s'appuie sur pandas pour les jeux de données
tabulaires et on réserve les dataclasses aux objets métier unitaires
(situation d'un produit, instantané KPI, résultat de simulation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Importateur:
    importateur_id: str
    nom: str
    zone: str
    commercial: str

    @property
    def label(self) -> str:
        return f"{self.nom} — {self.zone}"


@dataclass
class KpiSnapshot:
    """Instantané des KPI d'un produit issu de GOLD_CONSEIL_STOCK."""

    stock_actuel: Optional[float] = None
    ventes_moy_mensuelles: Optional[float] = None
    couverture_jours: Optional[float] = None
    rotation_annuelle: Optional[float] = None
    ecart_prevision_reel_pct: Optional[float] = None
    score_risque: Optional[float] = None  # échelle 0..1
    statut: Optional[str] = None

    @property
    def score_100(self) -> Optional[int]:
        """Score d'immobilisation exprimé sur 100 (récit de démonstration)."""
        return None if self.score_risque is None else int(round(self.score_risque * 100))


@dataclass
class SimulationResult:
    """Résultat d'une simulation de vente : situation avant / après."""

    importateur_id: str
    ean: str
    libelle: str
    mois: str
    quantite_avant: Optional[float]
    quantite_apres: float
    avant: KpiSnapshot
    apres: KpiSnapshot
    explication: str = ""


@dataclass
class MarketingDoc:
    """Document marketing remonté par Cortex Search."""

    doc_id: str
    titre: str
    zone: str
    gamme: str
    date_pub: str
    contenu: str
    score: float = 0.0


@dataclass
class AnalystAnswer:
    """Réponse de Cortex Analyst : texte, SQL généré, résultat tabulaire."""

    texte: str = ""
    sql: str = ""
    dataframe: object = None  # pandas.DataFrame
    suggestions: list = field(default_factory=list)
    erreur: str = ""
