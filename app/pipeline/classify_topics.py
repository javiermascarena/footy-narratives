# Purpose:
#  - Find article/team pairs that don't yet have a topic assigned.
#  - Compute SBERT embeddings for each article text.
#  - Predict topic label and probability with a saved sklearn pipeline.
#  - Upsert (insert or update) the prediction into the weekly_topic table.

from joblib import load
from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[2]   
sys.path.append(str(project_root))
from app.db import get_conn

# Logging setup (helps debugging)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths / model names / constants
BASE_DIR = Path(__file__).resolve().parents[2]   # repo root (adjust if different)
MODEL_DIR = BASE_DIR / "app" / "models"
MODEL_NAME = "topic_clf_v1_20250809T153500Z.joblib"   # adjust to your file
SBERT_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 256

# Query to upsert the rows
UPSERT_SQL = """
INSERT INTO weekly_topic
  (team_id, week_start, week_end, article_id, topic_id, topic_probability)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  topic_id = VALUES(topic_id),
  topic_probability = VALUES(topic_probability)
"""


def fetch_unlabeled_articles(cursor):
    """
    Fetch all (team_id, article_id, week_start, week_end, full_text) tuples
    for which weekly_topic.topic_id is NULL or the weekly_topic row doesn't exist.
    """
    query = """
    SELECT
        at.team_id,
        a.id AS article_id,
        DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY) AS week_start,
        DATE_ADD(
            DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY),
            INTERVAL 6 DAY
        ) AS week_end,
        a.full_text
    FROM article_teams at
    JOIN articles a ON a.id = at.article_id
    LEFT JOIN weekly_topic wt
        ON wt.article_id = a.id
        AND wt.team_id = at.team_id
        AND wt.week_start = DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY)
        AND wt.week_end   = DATE_ADD(DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY), INTERVAL 6 DAY)
    WHERE wt.topic_id IS NULL;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]
    # If no rows, return an empty DataFrame with the right columns
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def batch_iter(df, size):
    """Generator that yields dataframe batches"""
    for i in range(0, len(df), size):
        # "yield" returns one batch at a time to the caller (doesn't build all batches at once)
        yield df.iloc[i:i+size]
    

def main(): 
    # 1) locate and load the saved sklearn pipeline
    model_path = MODEL_DIR / MODEL_NAME
    if not model_path.exists():
        logger.error("Model file not found: %s", model_path)
        raise SystemExit(1)

    logger.info("Loading classifier: %s", model_path)
    clf = load(model_path)
    
    # 2) load SBERT model for embeddings
    logger.info("Loading SBERT model: %s", SBERT_MODEL)
    sbert = SentenceTransformer(SBERT_MODEL)

    # 3) connect to DB
    con = get_conn()
    cursor = con.cursor()

    # 4) fetch the list of rows to classify
    articles = fetch_unlabeled_articles(cursor)
    if articles.empty:
        logger.info("No articles to classify. Exiting.")
        cursor.close()
        con.close()
        return

    # 5) process in batches (memory-friendly)
    logger.info("Found %d articles to classify.", len(articles))
    upsert_rows = []

    for batch in batch_iter(articles, BATCH_SIZE):

        texts = batch["full_text"].tolist()
        # encode texts into embeddings
        emb = sbert.encode(texts, show_progress_bar=False)

        # get predictions and probabilities
        topic_preds = clf.predict(emb)
        topic_probs = clf.predict_proba(emb)

        # build the rows to upsert (match the UPSERT_SQL order)
        for i, row in enumerate(articles.itertuples(index=False)):
            article_id = int(row.article_id)
            team_id = int(row.team_id) 
            week_start = row.week_start   
            week_end = row.week_end
            pred_idx = int(topic_preds[i])
            pred_prob = float(np.max(topic_probs[i,]))

            upsert_rows.append(
                (team_id, week_start, week_end, article_id, pred_idx, pred_prob) #pred_prob
            )

    # 6) write results in a single transaction (executemany is faster than looped execute)
    if upsert_rows: 
        try:
            logger.info("Upserting %d weekly_topic rows...", len(upsert_rows))
            cursor.executemany(UPSERT_SQL, upsert_rows)

            con.commit()
            logger.info("DB commit successful.")
        except Exception as e:
            con.rollback()
            logger.exception("DB write error, rolled back: %s", e)
            raise
        finally:
            cursor.close()
            con.close()
    
    else: 
        logger.info("No rows to upsert.")
        cursor.close()
        con.close()



if __name__ == "__main__": 
    main()



