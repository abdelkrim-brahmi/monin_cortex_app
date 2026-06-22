"""Page 2 — Simulation de vente (cœur de la démonstration).

L'utilisateur saisit une nouvelle quantité vendue ; l'app écrit dans
SILVER_VENTES, la vue GOLD se recalcule, et les KPI sont affichés AVANT/APRÈS
avec une explication générée par Cortex Complete.

Gère aussi le scénario de démonstration automatique (bonus).
"""
from __future__ import annotations

import streamlit as st

from config import COLOR_OPPORTUNITY, COLOR_RISK, COLOR_NAVY
from models.entities import SimulationResult
from repository import stock_repository as repo
from services import simulation_service
from utils import ui, state
from utils.formatting import statut_badge_html

KEY_DEMO = "demo_request"


def render(session) -> None:
    ui.hero("🧪 Simulation en temps réel",
            "Saisissez une vente : KPI et niveau de risque recalculés en direct par Snowflake")

    if not state.require_importateur():
        return
    imp_id, label = state.get_importateur()

    demo = st.session_state.pop(KEY_DEMO, None)
    if demo:
        _run_demo_scenario(session, imp_id, label)
        return

    produits = repo.get_produits_importateur(session, imp_id)
    if produits.empty:
        st.warning("Aucun produit pour cet importateur.")
        return

    # ----- Formulaire de simulation --------------------------------------
    st.markdown(f"**Importateur :** {label}")
    c1, c2, c3 = st.columns([2, 1.4, 1])
    with c1:
        libelles = produits["LIBELLE"].tolist()
        idx = st.selectbox("Produit", range(len(libelles)),
                           format_func=lambda i: libelles[i], key="sim_prod")
        ean = produits.iloc[idx]["EAN"]
    with c2:
        mois_df = repo.get_mois_ventes(session, imp_id, ean)
        mois_options = [str(m) for m in mois_df["MOIS"].tolist()] if not mois_df.empty else []
        mois = st.selectbox("Mois", mois_options) if mois_options else st.text_input("Mois (YYYY-MM-DD)")
    with c3:
        q_actuelle = 0.0
        if mois_options and mois:
            row = mois_df[mois_df["MOIS"].astype(str) == mois]
            if not row.empty:
                q_actuelle = float(row.iloc[0]["QUANTITE"])
        nouvelle_q = st.number_input("Nouvelle quantité vendue", min_value=0.0,
                                     value=float(q_actuelle), step=10.0)

    st.caption(f"Quantité actuelle pour ce mois : **{q_actuelle:g}** → nouvelle : **{nouvelle_q:g}**")

    if st.button("⚡ Simuler la vente", type="primary", use_container_width=True):
        if not mois:
            st.error("Sélectionnez un mois.")
            return
        with st.spinner("Écriture de la vente, recalcul de la vue GOLD et analyse IA…"):
            result = simulation_service.simuler_vente(
                session, imp_id, ean, mois, nouvelle_q, model=state.get_model())
        st.session_state[state.KEY_LAST_SIM] = result
        st.toast("Vente simulée — KPI recalculés ✅")

    # ----- Affichage du dernier résultat ---------------------------------
    result = st.session_state.get(state.KEY_LAST_SIM)
    if isinstance(result, SimulationResult) and result.ean == ean:
        st.divider()
        render_result(result)


def render_result(result: SimulationResult) -> None:
    st.markdown(f"### Résultat — {result.libelle}")
    st.caption(f"Mois {result.mois} · quantité {result.quantite_avant or 0:g} → {result.quantite_apres:g}")

    cols = st.columns(4)
    _ba_card(cols[0], "Couverture", result.avant.couverture_jours, result.apres.couverture_jours, " j", "down")
    _ba_card(cols[1], "Score risque /100", result.avant.score_100, result.apres.score_100, "", "down")
    _ba_card(cols[2], "Rotation", result.avant.rotation_annuelle, result.apres.rotation_annuelle, "×", "up")
    with cols[3]:
        st.markdown("<div class='ba-card'><div class='kpi-label'>Statut</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='margin:.4rem 0'>{statut_badge_html(result.avant.statut)}</div>"
            f"<div class='ba-arrow'>↓</div>"
            f"<div style='margin:.4rem 0'>{statut_badge_html(result.apres.statut)}</div></div>",
            unsafe_allow_html=True,
        )

    if result.explication:
        ui.ai_box(result.explication, "💡 Explication générée par Cortex Complete")


def _ba_card(col, label: str, avant, apres, unit: str, better: str) -> None:
    """Carte AVANT → APRÈS avec coloration selon l'amélioration."""
    def fmt(v):
        if v is None:
            return "—"
        return f"{v:g}{unit}" if isinstance(v, float) else f"{v}{unit}"

    improved = None
    if avant is not None and apres is not None and avant != apres:
        improved = (apres < avant) if better == "down" else (apres > avant)
    css = "ba-after-neutral" if improved is None else ("ba-after-good" if improved else "ba-after-bad")

    col.markdown(
        f"<div class='ba-card'><div class='kpi-label'>{label}</div>"
        f"<div class='ba-before'>{fmt(avant)}</div>"
        f"<div class='ba-arrow'>↓</div>"
        f"<div class='{css}'>{fmt(apres)}</div></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Scénario de démonstration automatique (bonus)
# --------------------------------------------------------------------------- #
def _run_demo_scenario(session, imp_id, label) -> None:
    st.info(f"🎬 **Scénario de démonstration** — Importateur ciblé : **{label}**")

    cible = repo.get_produit_top_risque(session, imp_id)
    if not cible:
        st.warning("Aucun produit à risque pour ce scénario.")
        return
    ean = cible["EAN"]
    libelle = cible["LIBELLE"]

    # Mois le plus récent + vente importante (≈ 4× la moyenne mensuelle).
    mois_df = repo.get_mois_ventes(session, imp_id, ean)
    mois = str(mois_df.iloc[0]["MOIS"]) if not mois_df.empty else None
    base = float(cible.get("VENTES_MOY_MENSUELLES") or 100)
    grosse_vente = round(max(base * 4, base + 300))

    st.markdown(f"**1️⃣ Situation initiale** — produit le plus à risque : *{libelle}* "
                f"(couverture {cible.get('COUVERTURE_JOURS', 'N/A')} j, "
                f"score {int(round((cible.get('SCORE_RISQUE_IMMOBILISATION') or 0) * 100))}/100)")
    st.markdown(f"**2️⃣ Simulation d'une vente importante** : {grosse_vente:g} unités sur {mois}")

    with st.spinner("Recalcul des KPI et génération de l'analyse IA…"):
        result = simulation_service.simuler_vente(
            session, imp_id, ean, mois, grosse_vente, model=state.get_model())
    st.session_state[state.KEY_LAST_SIM] = result

    st.markdown("**3️⃣ KPI recalculés**")
    render_result(result)

    # Prépare la question préremplie pour l'assistant.
    st.session_state[state.KEY_CHAT_PREFILL] = "Pourquoi les recommandations ont-elles changé ?"

    st.divider()
    st.markdown("**4️⃣ Étapes suivantes**")
    cc1, cc2 = st.columns(2)
    if cc1.button("🤖 Générer la recommandation IA", use_container_width=True):
        state.goto("Recommandations IA")
        st.rerun()
    if cc2.button("💬 Ouvrir l'assistant (question préremplie)", use_container_width=True):
        state.goto("Assistant IA")
        st.rerun()
