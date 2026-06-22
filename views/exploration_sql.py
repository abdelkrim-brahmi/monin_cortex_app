"""Page 5 — Exploration SQL.

Console SQL : requête, résultat, plan d'exécution et temps d'exécution.
Lecture seule recommandée (l'app vise la démonstration analytique).
"""
from __future__ import annotations

import streamlit as st

from config import V_GOLD, T_VENTES, T_STOCK, T_PREVISIONS, T_MARKETING
from repository import stock_repository as repo
from utils import ui

EXEMPLES = {
    "Top 10 risques (toutes zones)": f"""SELECT importateur, libelle, gamme, couverture_jours,
       rotation_annuelle, score_risque_immobilisation, statut
FROM {V_GOLD}
ORDER BY score_risque_immobilisation DESC NULLS LAST
LIMIT 10""",
    "Surstock (couverture > 150 j)": f"""SELECT importateur, libelle, couverture_jours, stock_actuel
FROM {V_GOLD}
WHERE couverture_jours > 150
ORDER BY couverture_jours DESC
LIMIT 50""",
    "Écart prévision / réel": f"""SELECT importateur, libelle, reel_mois_courant, prevu_mois_courant,
       ecart_prevision_reel_pct
FROM {V_GOLD}
WHERE ecart_prevision_reel_pct IS NOT NULL
ORDER BY ABS(ecart_prevision_reel_pct) DESC
LIMIT 50""",
    "Rotation moyenne par importateur": f"""SELECT importateur, ROUND(AVG(rotation_annuelle),2) AS rotation_moy,
       COUNT(*) AS nb_produits
FROM {V_GOLD}
GROUP BY importateur
ORDER BY rotation_moy DESC""",
}


def render(session) -> None:
    ui.hero("🛠️ Exploration SQL",
            "Interrogez directement le modèle MONIN — requête, résultat, plan et durée")

    st.caption("Objets disponibles : "
               f"`{V_GOLD}` · `{T_VENTES}` · `{T_STOCK}` · `{T_PREVISIONS}` · `{T_MARKETING}` "
               "(les tables *_STG sont exclues).")

    choix = st.selectbox("Requête d'exemple", ["—"] + list(EXEMPLES.keys()))
    defaut = EXEMPLES.get(choix, f"SELECT * FROM {V_GOLD} LIMIT 100")

    sql = st.text_area("Requête SQL", value=defaut, height=200, key=f"sql_{choix}")

    if st.button("▶️ Exécuter", type="primary"):
        if not sql.strip():
            st.error("Saisissez une requête.")
            return
        try:
            with st.spinner("Exécution…"):
                res = repo.run_sql(session, sql)
        except Exception as e:  # noqa: BLE001
            st.error(f"Erreur d'exécution : {e}")
            return

        m1, m2 = st.columns(2)
        m1.metric("⏱️ Temps d'exécution", f"{res['elapsed'] * 1000:.0f} ms")
        m2.metric("📊 Lignes renvoyées", f"{len(res['dataframe'])}")

        tab_res, tab_plan = st.tabs(["📊 Résultat", "🧠 Plan d'exécution"])
        with tab_res:
            st.dataframe(res["dataframe"], use_container_width=True, hide_index=True)
        with tab_plan:
            st.code(res["plan"], language="text")
