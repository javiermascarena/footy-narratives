#!/usr/bin/env python3
from pathlib import Path
import mysql.connector
import pandas as pd
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "data" / "articles_labeled.csv"
TEAM_ID_MAP = {"Arsenal": 1, "Chelsea": 2, "Liverpool": 3,
               "Manchester City": 4, "Manchester United": 5, "Tottenham Hotspur": 6}

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", "appuserpass"),
    "database": os.getenv("DB_NAME", "footy_narratives"),
}

UPSERT_SQL = """
INSERT INTO weekly_topic
  (team_id, week_start, week_end, article_id, topic_id, topic_probability)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  topic_id = VALUES(topic_id),
  topic_probability = VALUES(topic_probability)
"""

def load_article_team_rows(cursor) -> pd.DataFrame:
    query = """
    SELECT 
        at.article_id,
        at.team_id,
        DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY) AS week_start,
        DATE_ADD(
            DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY),
            INTERVAL 6 DAY
        ) AS week_end
    FROM article_teams at
    JOIN articles a ON a.id = at.article_id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

def prepare_labeled(csv_path: Path) -> pd.DataFrame:
    # Read CSV with the params you used
    df = pd.read_csv(csv_path, sep=";", encoding="utf-16", engine="python")
    # Normalize column names to lowercase so we avoid case issues
    df.columns = [c.strip().lower() for c in df.columns]

    # Print columns if debugging
    logger.info("Loaded CSV columns: %s", df.columns.tolist())

    # Accept CSV fields 'article_id' or 'article_id' spelled 'Article_ID' (we normalized)
    if "article_id" not in df.columns or "topic" not in df.columns:
        raise SystemExit("CSV must contain columns 'Article_ID' and 'Topic' (case-insensitive).")

    # If we have textual team names in column 'team', map them -> team_id using TEAM_ID_MAP
    if "team" in df.columns and "team_id" not in df.columns:
        df["team_id"] = df["team"].map(lambda x: TEAM_ID_MAP.get(x.strip()) if isinstance(x, str) else None)
    elif "team_id" in df.columns:
        # ensure team_id column exists and is int-like
        df["team_id"] = df["team_id"].apply(lambda x: int(str(x).strip()) if str(x).strip() != "" else None)


    # Coerce article_id and topic to ints where possible
    df["article_id"] = df["article_id"].astype(int)
    df["topic"] = df["topic"].astype(int)

    # Keep columns article_id, team_id, topic
    if "team_id" not in df.columns:
        raise SystemExit("No 'team_id' available in CSV. Provide team_id column or a 'team' column that can be mapped.")
    return df[["article_id", "team_id", "topic"]].dropna(subset=["team_id"])

def main(dry_run=True):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(buffered=True)

    try:
        article_team_df = load_article_team_rows(cursor)
        if article_team_df.empty:
            logger.info("No article-team rows found in DB.")
            return

        labeled = prepare_labeled(CSV_PATH)

        # Ensure dtypes match for merging
        article_team_df["article_id"] = article_team_df["article_id"].astype(int)
        article_team_df["team_id"] = article_team_df["team_id"].astype(int)
        labeled["article_id"] = labeled["article_id"].astype(int)
        labeled["team_id"] = labeled["team_id"].astype(int)

        logger.info("article_team_df rows: %d, labeled rows (after mapping): %d", len(article_team_df), len(labeled))

        # Merge on keys
        merged = pd.merge(article_team_df, labeled, on=["article_id", "team_id"], how="inner")
        logger.info("Merged rows (to upsert): %d", len(merged))

        # Report if many labeled rows had no match in DB
        labeled_keys = set(zip(labeled["article_id"], labeled["team_id"]))
        db_keys = set(zip(article_team_df["article_id"], article_team_df["team_id"]))
        missing = labeled_keys - db_keys
        if missing:
            logger.warning("There are %d labeled (article_id,team_id) pairs not present in DB. Example: %s",
                           len(missing), list(missing)[:5])

        # Prepare upsert rows
        upsert_rows = []
        for r in merged.itertuples(index=False):
            # convert date types to string 'YYYY-MM-DD' for safety
            ws = r.week_start
            we = r.week_end
            upsert_rows.append((int(r.team_id), ws, we, int(r.article_id), int(r.topic), 1.0))

        logger.info("Prepared %d upsert rows. Preview: %s", len(upsert_rows), upsert_rows[:5])
        if dry_run:
            logger.info("Dry run enabled. Not writing to DB.")
            return

        cursor.executemany(UPSERT_SQL, upsert_rows)
        conn.commit()
        logger.info("Upserted %d rows into weekly_topic", len(upsert_rows))

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main(dry_run=False)  # set to False to actually write
