"""Page 1 — Dashboard importateur.

Vue 360° d'un importateur : KPI d'en-tête, graphiques d'évolution, et tableau
détaillé issu de GOLD_CONSEIL_STOCK. Aucun SQL ici (couche Repository only).
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from config import COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_RISK, COLOR_OPPORTUNITY, COLOR_NAVY
from repository import stock_repository as repo
from utils import ui, state
from utils.formatting import fr_number, fr_money, statut_badge_html


def render(session) -> None:
    ui.hero("📊 Tableau de bord importateur",
            "Vue 360° de la situation des stocks — préparez votre rendez-vous client")

    if not state.require_importateur():
        return
    imp_id, label = state.get_importateur()
    st.caption(f"Importateur sélectionné : **{label}**")

    resume = repo.get_resume(session, imp_id)

    # ----- Cartes KPI -----------------------------------------------------
    ca_label = "CA (12 mois)" if resume.get("ca_is_revenue") else "Volume vendu (12 mois)"
    ca_value = fr_money(resume["ca"]) if resume.get("ca_is_revenue") else fr_number(resume["ca"], " u.")
    ui.render_kpis([
        ui.kpi_card("Produits", fr_number(resume["NB_PRODUITS"]), "📦"),
        ui.kpi_card(ca_label, ca_value, "💶"),
        ui.kpi_card("Stock total", fr_number(resume["STOCK_TOTAL"], " u."), "🏬"),
        ui.kpi_card("Prév. mois +1", fr_number(resume["PREV_TOTAL"], " u."), "🔮"),
    ])
    st.write("")
    ui.render_kpis([
        ui.kpi_card("Produits à risque", fr_number(resume["NB_RISQUE"]), "🔴",
                    sub="immobilisation", color=COLOR_RISK),
        ui.kpi_card("Opportunités", fr_number(resume["NB_OPPORTUNITE"]), "🟢",
                    sub="à pousser", color=COLOR_OPPORTUNITY),
        ui.kpi_card("Couverture moy.", fr_number(resume["COUVERTURE_MOY"], " j", 0), "📆"),
        ui.kpi_card("Rotation moy.", fr_number(resume["ROTATION_MOY"], "×", 2), "🔄"),
    ])

    st.divider()

    # ----- Graphiques -----------------------------------------------------
    ventes = repo.get_ventes_mensuelles(session, imp_id)
    stock = repo.get_stock_mensuel(session, imp_id)
    conseil = repo.get_conseil(session, imp_id)

    c1, c2 = st.columns(2)
    with c1:
        ui.section("Évolution des ventes", "📈")
        if not ventes.empty:
            fig = px.area(ventes, x="MOIS", y="QUANTITE", markers=True)
            fig.update_traces(line_color=COLOR_PRIMARY, fillcolor="rgba(41,181,232,.15)")
            _style(fig, "Unités vendues")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        ui.section("Évolution du stock", "📉")
        if not stock.empty:
            fig = px.line(stock, x="MOIS", y="QUANTITE_STOCK", markers=True)
            fig.update_traces(line_color=COLOR_PRIMARY_DARK)
            _style(fig, "Unités en stock")
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        ui.section("Rotation par produit", "🔄")
        top = conseil.dropna(subset=["ROTATION_ANNUELLE"]).nlargest(12, "ROTATION_ANNUELLE")
        if not top.empty:
            fig = px.bar(top, x="ROTATION_ANNUELLE", y="LIBELLE", orientation="h",
                         color="ROTATION_ANNUELLE", color_continuous_scale="Blues")
            _style(fig, "Rotation annuelle (×)")
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
    with c4:
        ui.section("Couverture par produit", "📆")
        cov = conseil.dropna(subset=["COUVERTURE_JOURS"]).nlargest(12, "COUVERTURE_JOURS")
        if not cov.empty:
            fig = px.bar(cov, x="COUVERTURE_JOURS", y="LIBELLE", orientation="h",
                         color="COUVERTURE_JOURS", color_continuous_scale="Tealrose")
            _style(fig, "Couverture (jours)")
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ----- Tableau détaillé GOLD -----------------------------------------
    ui.section("Détail GOLD_CONSEIL_STOCK", "📋")
    filtre = st.multiselect("Filtrer par statut", ["à risque", "opportunité", "normal"],
                            default=["à risque", "opportunité"])
    table = conseil[conseil["STATUT"].isin(filtre)] if filtre else conseil
    st.dataframe(
        table,
        use_container_width=True, hide_index=True,
        column_config={
            "EAN": "EAN",
            "LIBELLE": "Produit",
            "GAMME": "Gamme",
            "STATUT_PRODUIT": "Statut produit",
            "STOCK_ACTUEL": st.column_config.NumberColumn("Stock", format="%d"),
            "VENTES_MOY_MENSUELLES": st.column_config.NumberColumn("Ventes moy./mois", format="%.1f"),
            "COUVERTURE_JOURS": st.column_config.NumberColumn("Couv. (j)", format="%d"),
            "ROTATION_ANNUELLE": st.column_config.NumberColumn("Rotation", format="%.2f"),
            "PREVISION_MOIS_SUIVANT": st.column_config.NumberColumn("Prév. M+1", format="%d"),
            "ECART_PREVISION_REEL_PCT": st.column_config.NumberColumn("Écart prév/réel %", format="%d%%"),
            "SCORE_RISQUE_IMMOBILISATION": st.column_config.ProgressColumn(
                "Score risque", min_value=0, max_value=1, format="%.2f"),
            "STATUT": "Statut",
        },
    )


def _style(fig, ytitle: str) -> None:
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title=None, yaxis_title=ytitle, font=dict(color=COLOR_NAVY),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF3F9")
