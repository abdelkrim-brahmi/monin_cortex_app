"""Helpers de formatage (nombres, deltas, statuts)."""
from __future__ import annotations

from config import STATUT_STYLE, COLOR_NORMAL


def fr_number(value, suffix: str = "", decimals: int = 0) -> str:
    """Formate un nombre à la française (espace fine comme séparateur de milliers)."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals == 0:
        s = f"{v:,.0f}".replace(",", " ")
    else:
        s = f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{s}{suffix}"


def fr_money(value) -> str:
    if value is None:
        return "—"
    v = float(value)
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.2f} M€".replace(".", ",")
    if abs(v) >= 1_000:
        return f"{v / 1_000:.1f} k€".replace(".", ",")
    return f"{v:.0f} €"


def statut_badge_html(statut: str) -> str:
    color, icon = STATUT_STYLE.get((statut or "").lower(), (COLOR_NORMAL, "⚪"))
    return (
        f"<span style='background:{color}1A;color:{color};padding:2px 10px;"
        f"border-radius:12px;font-size:0.8rem;font-weight:600;white-space:nowrap'>"
        f"{icon} {statut or 'n/a'}</span>"
    )


def delta_text(avant, apres, unit: str = "", better: str = "down"):
    """Renvoie (texte_delta, est_amélioration) pour l'affichage avant/après."""
    if avant is None or apres is None:
        return ("—", None)
    diff = apres - avant
    arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "▬")
    improved = None
    if diff != 0:
        improved = (diff < 0) if better == "down" else (diff > 0)
    return (f"{arrow} {diff:+.0f}{unit}", improved)
