#!/usr/bin/env python3
# app/schema/run_migrations.py
import os
from pathlib import Path
import mysql.connector
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB config - use env vars for flexibility
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),        
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", "appuserpass"),
    "database": os.getenv("DB_NAME", "footy_narratives"),
}

MIGRATIONS_DIR = Path(__file__).resolve().parents[0] / "migrations"

def get_migration_files():
    files = sorted([p for p in MIGRATIONS_DIR.iterdir() if p.suffix in (".sql",)], key=lambda p: p.name)
    return files

def ensure_schema_migrations(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
      id INT AUTO_INCREMENT PRIMARY KEY,
      filename VARCHAR(255) NOT NULL UNIQUE,
      applied_at DATETIME NOT NULL
    ) ENGINE=InnoDB;
    """)

def applied_files(cursor):
    cursor.execute("SELECT filename FROM schema_migrations")
    return {r[0] for r in cursor.fetchall()}

def apply_migration(cursor, sql_text, filename):
    # Remove comments and split on semicolon
    statements = [
        stmt.strip()
        for stmt in sql_text.split(";")
        if stmt.strip()
    ]
    for stmt in statements:
        cursor.execute(stmt)
    print(f"Applied migration: {filename}")

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    ensure_schema_migrations(cursor)
    conn.commit()

    applied = applied_files(cursor)
    files = get_migration_files()
    pending = [f for f in files if f.name not in applied]

    if not pending:
        logger.info("No new migrations to apply.")
    else:
        logger.info("Pending migrations: %s", [p.name for p in pending])
        for f in pending:
            logger.info("Applying %s...", f.name)
            sql_text = f.read_text(encoding="utf-8")
            try:
                apply_migration(cursor, sql_text, f.name)
                # record success
                cursor.execute(
                    "INSERT INTO schema_migrations (filename, applied_at) VALUES (%s, %s)",
                    (f.name, datetime.now())
                )
                conn.commit()
                logger.info("Applied %s", f.name)
            except Exception as e:
                conn.rollback()
                logger.exception("Failed applying %s: %s", f.name, e)
                raise

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
