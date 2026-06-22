-- =====================================================================
-- SETUP CORTEX — à exécuter UNE FOIS avant de lancer l'application.
-- Database MONIN / Schema PUBLIC. Rôle disposant de CREATE sur le schéma.
-- =====================================================================
USE DATABASE MONIN;
USE SCHEMA PUBLIC;
USE WAREHOUSE COMPUTE_WH;

-- ---------------------------------------------------------------------
-- 1) CORTEX SEARCH SERVICE sur les documents marketing (Page 4)
--    Indexe la colonne CONTENU ; DOC_ID/TITRE/ZONE/GAMME/DATE_PUB filtrables.
-- ---------------------------------------------------------------------
CREATE OR REPLACE CORTEX SEARCH SERVICE MONIN.PUBLIC.MONIN_MARKETING_SEARCH
  ON contenu
  ATTRIBUTES doc_id, titre, zone, gamme, date_pub
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  AS (
      SELECT doc_id, titre, zone, gamme, date_pub, contenu
      FROM MONIN.PUBLIC.SILVER_MARKETING
  );

-- Vérification rapide :
-- SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
--   'MONIN.PUBLIC.MONIN_MARKETING_SEARCH',
--   '{"query":"tendance boissons glacées asie","columns":["CONTENU","TITRE"],"limit":3}');

-- ---------------------------------------------------------------------
-- 2) STAGE pour le semantic model de Cortex Analyst (Page 3)
-- ---------------------------------------------------------------------
CREATE STAGE IF NOT EXISTS MONIN.PUBLIC.MONIN_SEMANTIC_MODELS
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- ---------------------------------------------------------------------
-- 3) DÉPÔT DU FICHIER monin_conseil_stock.yaml sur le stage
--    Le PUT ne fonctionne PAS dans un worksheet Snowsight. Trois options :
--
--    A. Snowsight UI : Data > Databases > MONIN > PUBLIC > Stages >
--       MONIN_SEMANTIC_MODELS > "+ Files" et téléverser le YAML.
--
--    B. SnowSQL :
--       snowsql -a A3857344721571-TEAMWORKCORP_PARTNER -u ABRAHMI \
--         -q "PUT file://sql/monin_conseil_stock.yaml @MONIN.PUBLIC.MONIN_SEMANTIC_MODELS AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
--
--    C. Python connector (depuis le dossier monin_cortex_app) :
--       voir scripts/upload_semantic_model.py
-- ---------------------------------------------------------------------

-- Vérifier la présence du fichier :
LS @MONIN.PUBLIC.MONIN_SEMANTIC_MODELS;

-- ---------------------------------------------------------------------
-- 4) (Optionnel) Droits pour le rôle qui exécutera l'app Streamlit
-- ---------------------------------------------------------------------
-- GRANT USAGE ON CORTEX SEARCH SERVICE MONIN.PUBLIC.MONIN_MARKETING_SEARCH TO ROLE <APP_ROLE>;
-- GRANT READ ON STAGE MONIN.PUBLIC.MONIN_SEMANTIC_MODELS TO ROLE <APP_ROLE>;
-- GRANT SELECT ON ALL TABLES IN SCHEMA MONIN.PUBLIC TO ROLE <APP_ROLE>;
-- GRANT SELECT ON VIEW MONIN.PUBLIC.GOLD_CONSEIL_STOCK TO ROLE <APP_ROLE>;
-- -- L'app écrit dans SILVER_VENTES (Page 2 — simulation) :
-- GRANT INSERT, UPDATE ON TABLE MONIN.PUBLIC.SILVER_VENTES TO ROLE <APP_ROLE>;
