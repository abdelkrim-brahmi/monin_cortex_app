"""Configuration centrale de l'application MONIN x Snowflake Cortex.

Toutes les constantes (base, schéma, objets, modèles Cortex, noms de services)
sont centralisées ici. Aucune valeur en dur ailleurs dans le code.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# Localisation des données
# --------------------------------------------------------------------------- #
DATABASE = "MONIN"
SCHEMA = "PUBLIC"
FQ = f"{DATABASE}.{SCHEMA}"  # préfixe pleinement qualifié

# Objets exploitables (les tables *_STG sont volontairement absentes).
T_PRODUIT = f"{FQ}.SILVER_PRODUIT"
T_IMPORTATEUR = f"{FQ}.SILVER_IMPORTATEUR"
T_VENTES = f"{FQ}.SILVER_VENTES"
T_STOCK = f"{FQ}.SILVER_STOCK"
T_PREVISIONS = f"{FQ}.SILVER_PREVISIONS"
T_MARKETING = f"{FQ}.SILVER_MARKETING"
V_GOLD = f"{FQ}.GOLD_CONSEIL_STOCK"

# --------------------------------------------------------------------------- #
# Cortex
# --------------------------------------------------------------------------- #
# Modèle Cortex Complete par défaut. Liste alignée sur les modèles Claude
# disponibles dans Snowflake Cortex. La disponibilité dépend de la région du
# compte ; activer "cross-region inference" si besoin. Sélectionnable dans l'UI.
DEFAULT_MODEL = "claude-3-5-sonnet"
AVAILABLE_MODELS = [
    "claude-3-5-sonnet",
    "claude-3-7-sonnet",
    "claude-4-sonnet",
    "claude-4-opus",
    "mistral-large2",
    "llama3.1-70b",
]

# Cortex Search : service indexant SILVER_MARKETING (créé via sql/02_*.sql).
CORTEX_SEARCH_SERVICE = f"{FQ}.MONIN_MARKETING_SEARCH"
SEARCH_TEXT_COLUMN = "CONTENU"
SEARCH_ATTR_COLUMNS = ["DOC_ID", "TITRE", "ZONE", "GAMME", "DATE_PUB"]

# Cortex Analyst : fichier de semantic model déposé sur ce stage (sql/01_*.sql).
SEMANTIC_MODEL_STAGE = f"{FQ}.MONIN_SEMANTIC_MODELS"
SEMANTIC_MODEL_FILE = "monin_conseil_stock.yaml"
SEMANTIC_MODEL_PATH = f"@{SEMANTIC_MODEL_STAGE}/{SEMANTIC_MODEL_FILE}"
ANALYST_ENDPOINT = "/api/v2/cortex/analyst/message"
ANALYST_TIMEOUT_MS = 50_000

# --------------------------------------------------------------------------- #
# Présentation
# --------------------------------------------------------------------------- #
APP_TITLE = "MONIN · Conseil Stock Intelligent"
APP_SUBTITLE = "Assistant IA pour le pilotage des stocks importateurs — propulsé par Snowflake Cortex"

# Palette Snowflake (bleu / blanc).
COLOR_PRIMARY = "#29B5E8"      # Snowflake blue
COLOR_PRIMARY_DARK = "#11567F"
COLOR_NAVY = "#1B2A4A"
COLOR_RISK = "#E8506E"
COLOR_OPPORTUNITY = "#2EB67D"
COLOR_NORMAL = "#7A8AA0"
COLOR_BG = "#F5F9FF"

# Mapping statut métier -> couleur / icône.
STATUT_STYLE = {
    "à risque": (COLOR_RISK, "🔴"),
    "opportunité": (COLOR_OPPORTUNITY, "🟢"),
    "normal": (COLOR_NORMAL, "⚪"),
}
