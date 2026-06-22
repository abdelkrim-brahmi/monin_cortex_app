"""Dépose le semantic model YAML sur le stage Cortex Analyst (PUT).

Usage :
    python scripts/upload_semantic_model.py

Réutilise la connexion externalbrowser du compte MONIN.
"""
from __future__ import annotations

import pathlib

import snowflake.connector

CONN = {
    "account": "A3857344721571-TEAMWORKCORP_PARTNER",
    "user": "ABRAHMI",
    "authenticator": "externalbrowser",
    "role": "SNOWFLAKE_INTELLIGENCE_ADMIN",
    "warehouse": "COMPUTE_WH",
    "database": "MONIN",
    "schema": "PUBLIC",
}

STAGE = "MONIN.PUBLIC.MONIN_SEMANTIC_MODELS"
YAML = pathlib.Path(__file__).resolve().parent.parent / "sql" / "monin_conseil_stock.yaml"


def main() -> None:
    cn = snowflake.connector.connect(**CONN)
    cur = cn.cursor()
    cur.execute(
        f"CREATE STAGE IF NOT EXISTS {STAGE} "
        "DIRECTORY = (ENABLE = TRUE) ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')"
    )
    uri = YAML.as_posix()
    cur.execute(f"PUT 'file://{uri}' @{STAGE} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
    print(cur.fetchall())
    cur.execute(f"LS @{STAGE}")
    for r in cur.fetchall():
        print(r)
    cur.close()
    cn.close()
    print("OK — semantic model déposé sur le stage.")


if __name__ == "__main__":
    main()
