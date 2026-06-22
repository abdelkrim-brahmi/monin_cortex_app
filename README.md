# MONIN · Conseil Stock Intelligent — Démo Snowflake Cortex

Application Streamlit de démonstration métier : **« Conseil à l'utilisation des
stocks pour les importateurs »**. Elle montre la valeur de Snowflake Cortex
(Complete, Analyst, Search) sur le modèle `MONIN.PUBLIC`.

> Le commercial prépare son rendez-vous importateur. L'IA l'aide à diagnostiquer
> les risques de stock, simuler une vente en direct, interroger la donnée en
> langage naturel et générer des recommandations enrichies par la veille marketing.

## Les 5 pages

| Page | Rôle | Cortex |
|------|------|--------|
| **📊 Dashboard** | Vue 360° importateur : KPI, graphiques, table GOLD | — |
| **🧪 Simulation** | Saisir une vente → recalcul live des KPI AVANT/APRÈS | **Complete** |
| **🤖 Assistant IA** | Questions en langage naturel → SQL + résultat + explication | **Analyst** |
| **🧭 Recommandations IA** | GOLD + docs marketing → recommandation citée | **Search + Complete** |
| **🛠️ Exploration SQL** | Console SQL : requête, résultat, plan, durée | — |

**Bonus** : bouton *🎬 Scénario de démonstration* (barre latérale) qui enchaîne
automatiquement sélection d'importateur → situation initiale → simulation d'une
grosse vente → recalcul → puis ouverture des recommandations / de l'assistant
avec une question préremplie.

## Architecture (couches)

```
app.py            Routeur + sélecteurs globaux (importateur, modèle Cortex)
config.py         Constantes (objets, modèles, services) — aucune valeur en dur ailleurs
views/            1 page = 1 fonction render(session). AUCUN SQL ici.
services/         Cortex Complete / Analyst / Search + orchestration simulation
repository/       TOUT le SQL (couche Repository centralisée) + session Snowpark unique
models/           Dataclasses de domaine
prompts/          Templates de prompts Cortex Complete
utils/            Design system (CSS Snowflake), formatage, état partagé
sql/              Setup Cortex + semantic model YAML
scripts/          Utilitaire de dépôt du semantic model
```

Principe clé : **aucune requête SQL dans les pages** — tout passe par
`repository/stock_repository.py`.

## Installation (Streamlit in Snowflake)

### 1. Setup Cortex (une fois)

Exécuter `sql/00_setup_cortex.sql` dans un worksheet Snowsight. Il crée :
- le **Cortex Search Service** `MONIN_MARKETING_SEARCH` sur `SILVER_MARKETING` ;
- le **stage** `MONIN_SEMANTIC_MODELS` pour le semantic model.

### 2. Déposer le semantic model Cortex Analyst

```bash
# depuis monin_cortex_app/
python scripts/upload_semantic_model.py
```
(ou via l'UI Snowsight : Stage `MONIN_SEMANTIC_MODELS` → *+ Files* → `sql/monin_conseil_stock.yaml`)

### 3. Déployer l'app

**Option A — Snowflake CLI** (recommandé) :
```bash
# depuis monin_cortex_app/
snow streamlit deploy --replace
```
(utilise `snowflake.yml` ; crée l'app `MONIN.PUBLIC.MONIN_CONSEIL_STOCK`)

**Option B — Snowsight** : Projects → Streamlit → *+ Streamlit App*, puis
téléverser le contenu du dossier (en conservant l'arborescence), fichier
principal `app.py`, packages depuis `environment.yml`.

### 4. Droits (si rôle applicatif dédié)

Voir la section 4 de `sql/00_setup_cortex.sql` (SELECT sur le schéma,
INSERT/UPDATE sur `SILVER_VENTES`, USAGE sur le Search Service, READ sur le stage).

## Exécution locale (développement)

Le code détecte automatiquement l'absence de SiS et bascule sur une session
Snowpark locale (`repository/connection.py`). Configurer une connexion nommée
`monin` dans `~/.snowflake/connections.toml`, puis :

```bash
pip install streamlit pandas plotly snowflake-snowpark-python
streamlit run app.py
```
> En local, Cortex Analyst (API REST interne) bascule en mode dégradé :
> le SQL est généré par Cortex Complete à partir du schéma. En SiS, le vrai
> Cortex Analyst est utilisé.

## Modèles Cortex

Sélecteur de modèle dans la barre latérale (défaut `claude-3-5-sonnet`). Si un
modèle n'est pas disponible dans votre région, en choisir un autre ou activer la
*cross-region inference* :
```sql
ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';
```

## Notes de conception

- **Simulation live** : `GOLD_CONSEIL_STOCK` étant une *vue*, un `MERGE` dans
  `SILVER_VENTES` suffit à recalculer tous les KPI au re-`SELECT`. Le cache de
  lecture est purgé après écriture.
- **Score de risque** : exprimé 0–1 dans la vue, affiché ×100 dans l'UI.
- **CA** : lu depuis `SILVER_VENTES.CA` (détection automatique de la colonne) ;
  l'`upsert` de simulation recalcule aussi le CA pour rester cohérent.
- **Images produits** : table `IMAGES` jointe par `PRODUCT_ID = SILVER_PRODUIT.EAN`
  (plusieurs visuels par produit, `POSITION` = ordre, 1 = principale).
  Image principale via `QUALIFY ROW_NUMBER()`. Visuels affichés dans le tableau
  (`ImageColumn`), la galerie risque, la simulation et les recommandations, avec
  fallback `IMAGE_PLACEHOLDER`.
- **Marque** : logo MONIN (barre latérale) et logo TeamWork (pied « Réalisé par »).
```
