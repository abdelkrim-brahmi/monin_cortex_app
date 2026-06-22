"""Page 4 — Recommandations IA (GOLD + Marketing via Cortex Search + Complete).

Pour un produit sélectionné : on retrouve les documents marketing pertinents
avec Cortex Search, puis Cortex Complete construit une recommandation
commerciale actionnable qui CITE les documents utilisés.
"""
from __future__ import annotations

import streamlit as st

from repository import stock_repository as repo
from services import cortex_search
from services.cortex_complete import complete
from prompts.templates import prompt_recommandation
from models.entities import KpiSnapshot
from utils import ui, state
from utils.formatting import fr_number, statut_badge_html


def render(session) -> None:
    ui.hero("🧭 Recommandations IA",
            "Cortex Search croise vos KPI avec la veille marketing pour recommander l'action commerciale")

    if not state.require_importateur():
        return
    imp_id, label = state.get_importateur()

    risques = repo.get_produits_a_risque(session, imp_id, limit=20)
    if risques.empty:
        st.info("Aucun produit à analyser pour cet importateur.")
        return

    st.markdown(f"**Importateur :** {label}")
    libelles = risques["LIBELLE"].tolist()
    idx = st.selectbox("Produit à analyser (triés par risque décroissant)",
                       range(len(libelles)), format_func=lambda i: libelles[i])
    produit = risques.iloc[idx].to_dict()

    # Aperçu KPI du produit.
    score100 = int(round((produit.get("SCORE_RISQUE_IMMOBILISATION") or 0) * 100))
    ui.render_kpis([
        ui.kpi_card("Couverture", fr_number(produit.get("COUVERTURE_JOURS"), " j"), "📆"),
        ui.kpi_card("Rotation", fr_number(produit.get("ROTATION_ANNUELLE"), "×", 2), "🔄"),
        ui.kpi_card("Score risque", f"{score100}/100", "⚠️"),
        ui.kpi_card("Stock", fr_number(produit.get("STOCK_ACTUEL"), " u."), "🏬"),
    ])
    st.markdown(f"Statut : {statut_badge_html(produit.get('STATUT'))}", unsafe_allow_html=True)

    st.write("")
    if st.button("🧭 Générer la recommandation", type="primary", use_container_width=True):
        _generer(session, produit)


def _generer(session, produit: dict) -> None:
    # Requête de recherche construite à partir du contexte produit.
    requete = f"{produit.get('LIBELLE','')} {produit.get('GAMME','')} tendance marché stock"
    with st.spinner("Cortex Search : recherche des documents marketing pertinents…"):
        docs = cortex_search.search_documents(
            session, requete, limit=4,
            zone=produit.get("ZONE"), gamme=produit.get("GAMME"))

    if docs:
        ui.section("Documents marketing identifiés", "🔎")
        st.markdown(
            " ".join(
                f"<span class='doc-chip'>📄 <b>{d.doc_id}</b> · {d.titre} "
                f"<i>({d.zone} · {d.gamme})</i></span>"
                for d in docs
            ),
            unsafe_allow_html=True,
        )
    else:
        st.warning("Aucun document marketing pertinent trouvé — recommandation basée sur les KPI seuls.")

    produit_ctx = {
        "libelle": produit.get("LIBELLE"), "gamme": produit.get("GAMME"),
        "statut": produit.get("STATUT"),
        "couverture_jours": produit.get("COUVERTURE_JOURS"),
        "rotation_annuelle": produit.get("ROTATION_ANNUELLE"),
        "score_100": int(round((produit.get("SCORE_RISQUE_IMMOBILISATION") or 0) * 100)),
        "stock_actuel": produit.get("STOCK_ACTUEL"),
        "ventes_moy_mensuelles": produit.get("VENTES_MOY_MENSUELLES"),
    }
    docs_ctx = [{
        "doc_id": d.doc_id, "titre": d.titre, "zone": d.zone,
        "gamme": d.gamme, "date_pub": d.date_pub, "contenu": d.contenu,
    } for d in docs]

    with st.spinner("Cortex Complete : rédaction de la recommandation…"):
        reco = complete(session, prompt_recommandation(produit_ctx, docs_ctx),
                        model=state.get_model())

    ui.ai_box(reco, "🧭 Recommandation commerciale")

    if docs:
        with st.expander("📚 Sources marketing citées (contenu intégral)"):
            for d in docs:
                st.markdown(f"**[{d.doc_id}] {d.titre}** — _{d.zone} · {d.gamme} · {d.date_pub}_")
                st.write(d.contenu)
                st.divider()
