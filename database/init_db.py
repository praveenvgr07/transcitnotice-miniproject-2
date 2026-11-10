"""Run schema.sql against the configured MySQL server."""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path so config is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

import mysql.connector
from config import get_config


def run_schema():
    cfg = get_config()
    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")

    # Connect WITHOUT specifying database (it may not exist yet)
    conn = mysql.connector.connect(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
        charset="utf8mb4",
        use_pure=True,
    )
    cursor = conn.cursor()

    with open(schema_file, "r", encoding="utf-8") as fh:
        sql_text = fh.read()

    # Split on semicolons, skip empty statements
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
            conn.commit()
        except mysql.connector.Error as exc:
            logger.warning("Skipped statement (%s): %.80s…", exc.errno, stmt)

    cursor.close()
    conn.close()
    logger.info("Database schema initialised successfully.")


if __name__ == "__main__":
    run_schema()
