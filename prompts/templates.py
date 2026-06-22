"""Templates de prompts pour Cortex Complete.

Centralise toute l'ingénierie de prompt afin de la versionner et l'ajuster
sans toucher aux services. Ton : expert supply-chain / category management,
en français, orienté action commerciale terrain.
"""
from __future__ import annotations

SYSTEM_PERSONA = (
    "Tu es l'assistant IA de MONIN, expert en gestion des stocks et category "
    "management pour les importateurs de sirops et sauces. Tu t'adresses à un "
    "commercial qui prépare un rendez-vous client. Réponds en français, de façon "
    "concise, factuelle et orientée action. N'invente aucun chiffre."
)


def prompt_explication_simulation(ctx: dict) -> str:
    """Explication métier AVANT/APRÈS d'une simulation de vente (Page 2)."""
    return f"""{SYSTEM_PERSONA}

Un commercial vient de simuler une vente supplémentaire pour préparer son rendez-vous.

Produit : {ctx['libelle']} (EAN {ctx['ean']})
Mois concerné : {ctx['mois']}
Quantité vendue — avant : {ctx['quantite_avant']} → après : {ctx['quantite_apres']}

Impact recalculé sur les indicateurs (source : GOLD_CONSEIL_STOCK) :
- Couverture (jours)         : {ctx['couv_avant']} → {ctx['couv_apres']}
- Rotation annuelle          : {ctx['rota_avant']} → {ctx['rota_apres']}
- Score de risque /100       : {ctx['score_avant']} → {ctx['score_apres']}
- Statut produit             : {ctx['statut_avant']} → {ctx['statut_apres']}

Rédige une explication de 3 à 4 phrases, claire et percutante, destinée au
commercial. Explique l'impact business de cette vente sur le risque
d'immobilisation et la couverture, et conclus sur ce que cela change pour le
rendez-vous. Mets en gras les chiffres clés.
"""


def prompt_recommandation(produit: dict, docs: list[dict]) -> str:
    """Recommandation commerciale enrichie par les documents marketing (Page 4)."""
    docs_txt = "\n\n".join(
        f"[{d['doc_id']}] « {d['titre']} » (zone {d['zone']}, gamme {d['gamme']}, {d['date_pub']})\n{d['contenu']}"
        for d in docs
    ) or "(aucun document marketing pertinent trouvé)"

    return f"""{SYSTEM_PERSONA}

Voici la situation d'un produit pour un importateur (source GOLD_CONSEIL_STOCK) :
- Produit          : {produit['libelle']} (gamme {produit.get('gamme', 'N/A')})
- Statut           : {produit.get('statut', 'N/A')}
- Couverture       : {produit.get('couverture_jours', 'N/A')} jours
- Rotation annuelle: {produit.get('rotation_annuelle', 'N/A')}
- Score de risque  : {produit.get('score_100', 'N/A')}/100
- Stock actuel     : {produit.get('stock_actuel', 'N/A')} unités
- Ventes moy./mois : {produit.get('ventes_moy_mensuelles', 'N/A')} unités

Documents marketing récupérés par Cortex Search (les plus pertinents) :
{docs_txt}

Produis une recommandation commerciale actionnable structurée ainsi :
1. **Diagnostic** : 2 phrases sur la situation (risque/opportunité) en t'appuyant
   sur les KPI.
2. **Insight marché** : ce que disent les documents marketing, en CITANT
   explicitement leur identifiant entre crochets (ex : [MKT001]).
3. **Plan d'action** : 3 à 4 puces concrètes (campagne, ciblage, promotion,
   opération saisonnière) cohérentes avec le diagnostic ET les documents.

Sois spécifique, jamais générique. N'utilise que les documents fournis ; si
aucun n'est pertinent, dis-le explicitement.
"""


def prompt_explication_resultat(question: str, sql: str, apercu: str) -> str:
    """Explication en langage naturel d'un résultat de requête (Page 3)."""
    return f"""{SYSTEM_PERSONA}

Question de l'utilisateur : « {question} »

Requête SQL exécutée :
{sql}

Aperçu du résultat (premières lignes) :
{apercu}

En 2 à 4 phrases, explique le résultat à l'utilisateur de façon métier, en
mettant en avant les enseignements clés (produits à risque, tendances,
recommandations implicites). Ne répète pas la requête SQL.
"""


def prompt_sql_fallback(question: str, schema_hint: str) -> str:
    """Génération de SQL si Cortex Analyst est indisponible (mode dégradé)."""
    return f"""Tu es un générateur SQL Snowflake. Génère UNIQUEMENT une requête
SQL Snowflake valide (aucun texte autour, pas de balises markdown) répondant à
la question, en lecture seule (SELECT), en utilisant exclusivement ces objets :

{schema_hint}

Contraintes :
- Utilise les noms pleinement qualifiés MONIN.PUBLIC.*
- N'utilise jamais les tables suffixées _STG.
- Ajoute toujours une clause LIMIT 100 si la requête peut renvoyer beaucoup de lignes.

Question : {question}

SQL :"""
