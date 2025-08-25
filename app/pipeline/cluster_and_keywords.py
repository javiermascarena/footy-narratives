# Purpose:
#  - Find article/team pairs that don't yet have a cluster assigned.
#  - Compute weekly cluster with KMeans.
#  - Compute keywords per cluster
#  - Upsert (insert or update) the prediction into the weekly_topic, weekly_clusters and weekly_keywords tables.

from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from keybert import KeyBERT
import spacy
from sklearn.cluster import KMeans
from sklearn.preprocessing import OneHotEncoder
import re
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
SBERT_MODEL = "all-MiniLM-L6-v2"
KEYBERT_MODEL = "distilbert-base-nli-mean-tokens"
SPACY_MODEL = "en_core_web_sm"

# table_names
TABLE_WEEKLY_TOPIC = "weekly_topic"
TABLE_WEEKLY_CLUSTER = "weekly_clusters"
TABLE_WEEKLY_KEYWORDS = "weekly_keywords"

# Define team aliases for filtering keywords
TEAM_ALIASES = {
    1: r"\b(?:Arsenal|Gunners)\b",
    2: r"\b(?:Chelsea|Blues)\b",
    3: r"\b(?:Liverpool|Reds)\b",
    4: r"\b(?:Manchester City|Man City)\b",
    5: r"\b(?:Manchester United|Man Utd|Red Devils|Man United)\b",
    6: r"\b(?:Tottenham Hotspur|Spurs|Tottenham)\b"
}

# Query to upsert the rows
UPSERT_WEEKLY_TOPICS = f"""
INSERT INTO {TABLE_WEEKLY_TOPIC}
  (team_id, week_start, week_end, article_id, cluster_id)
VALUES (%s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  cluster_id = VALUES(cluster_id)
"""
UPSERT_WEEKLY_CLUSTERS = f"""
INSERT INTO {TABLE_WEEKLY_CLUSTER}
  (team_id, week_start, week_end, cluster_id, size)
VALUES (%s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  size = VALUES(size)
"""
UPSERT_WEEKLY_KEYWORDS = f"""
INSERT INTO {TABLE_WEEKLY_KEYWORDS}
  (team_id, week_start, week_end, cluster_id, keyword, score)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  score = VALUES(score)
"""


def fetch_unlabeled_articles(cursor):
    """
    Fetch all (team_id, article_id, week_start, week_end, full_text) tuples
    for which weekly_topic.cluster_id is NULL or the weekly_topic row doesn't exist.
    """
    # cannot select articles of this week
    query = """
    SELECT
    at.team_id,
    a.id AS article_id,
    DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY) AS week_start,
    DATE_ADD(
        DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY),
        INTERVAL 6 DAY
    ) AS week_end,
    a.full_text,
    wt.topic_id
    FROM article_teams at
    JOIN articles a ON a.id = at.article_id
    LEFT JOIN weekly_topic wt
    ON wt.article_id = a.id
    AND wt.team_id = at.team_id
    AND wt.week_start = DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY)
    AND wt.week_end   = DATE_ADD(DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY), INTERVAL 6 DAY)
    WHERE wt.cluster_id IS NULL
    AND DATE_ADD(
        DATE_SUB(DATE(a.publication_date), INTERVAL WEEKDAY(a.publication_date) DAY),
        INTERVAL 6 DAY
    ) < CURDATE()
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]
    # If no rows, return an empty DataFrame with the right columns
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def elbow_best_k(lower_bound, inertias): 
    """ 
    Calculate the best k based on the distance to the line method.

    Args:
        lower_bound (int): the first k value
        inertias (list): List of inertia values for different k values.
    Returns:
        int: The best k value based on the maximum distance to the linear inertia.
    """

    # Get the first and last inertia values
    lowest_inertia = inertias[-1]
    highest_inertia = inertias[0]

    # If there are not enough inertias, return 0
    if len(inertias) < 2:
        return lower_bound
    
    # Calculate the step size for linear interpolation
    step = (highest_inertia - lowest_inertia) / (len(inertias)-1)

    # Initialize variables to track the maximum distance and the best k
    max_distance = -np.inf
    best_k = 0

    # Iterate through the inertias to find the best k
    for i in range(len(inertias)):
        # Calculate the linear inertia
        linear_inertia = highest_inertia - i * step
        # Calculate the distance from the linear inertia
        distance = abs(inertias[i] - linear_inertia)

        # Update the maximum distance and best k if the current distance is greater
        if distance > max_distance:
            max_distance = distance
            best_k = i 

    return lower_bound + best_k


def filter_and_dedup(keywords, alias_pattern):
    """ Remove any kw matching alias_pattern,
        then dedupe so no kw is substring of another. """
    
    # Exclude team mentions
    filtered = [(kw, float(score)) for kw, score in keywords
                if not alias_pattern.search(kw)]
    # Sort by length descending (so longer phrases absorb shorter ones)
    filtered = sorted(filtered, key=lambda ks: (len(ks[0]), ks[1]), reverse=True)
    unique = []
    for kw, score in filtered:
        # Keep kw only if it doesn't fully contain—or isn't contained by—an already kept kw
        if not any((kw.lower() in u.lower()) or (u.lower() in kw.lower()) for u, _ in unique):
            unique.append((kw, score))
    return unique


def main():   
    # load models
    logger.info("Loading SBERT model: %s", SBERT_MODEL)
    sbert = SentenceTransformer(SBERT_MODEL)
    nlp = spacy.load(SPACY_MODEL)
    kw_model = KeyBERT(KEYBERT_MODEL)

    # connect to DB
    con = get_conn()
    cursor = con.cursor()

    # fetch the list of rows to classify
    articles = fetch_unlabeled_articles(cursor)
    if articles.empty:
        logger.info("No articles to classify. Exiting.")
        cursor.close()
        con.close()
        return

    logger.info("Found %d articles to classify.", len(articles))

    # ensure correct dtypes and column names
    # expected columns: team_id, article_id, week_start, week_end, full_text, topic_id
    for col in ["team_id","article_id","week_start","week_end","full_text","topic_id"]:
        if col not in articles.columns:
            logger.error("Missing column %s in fetched data", col)
            return

    # ------------------------
    # FULL CLUSTERING PIPELINE
    # ------------------------

    articles["cluster_id"] = np.nan

    cluster_rows = []
    keyword_rows = []
    topic_rows = []

    enc = OneHotEncoder(handle_unknown='ignore')
    for (team_id, week_start, week_end), group in articles.groupby(["team_id", "week_start", "week_end"]):
        # Check if there are enough articles to cluster
        n_articles = group["article_id"].nunique()
        if n_articles < 2: 
            logger.info("Team %s week %s has <2 articles (n=%d). clustering all as 0.", team_id, week_start, n_articles)
            articles.loc[group.index, "cluster_id"] = [0 for _ in range(len(group))]
            continue

        # Embed the full text and one-hot encode the topics to create the feature matri
        X_emb = sbert.encode(group["full_text"].tolist())
        topic_encoded = enc.fit_transform(group[["topic_id"]]).toarray()
        X = np.concatenate((X_emb, topic_encoded), axis=1)

        # Putting a lower and upper bound on k
        lower_bound = 2
        upper_bound = max(lower_bound, n_articles // 2)
        k = range(lower_bound, upper_bound + 1)

        # Perform KMeans and GMM clustering
        inertias = []
        for n_clusters in k: 
            km = KMeans(n_clusters=n_clusters, random_state=42)
            km.fit(X)
            inertias.append(km.inertia_)

        # Calculate the optimal k for KMeans and fit the model
        optimal_k = elbow_best_k(lower_bound, inertias)
        logger.info("Team %s week %s: n=%d optimal_k=%d", team_id, week_start, n_articles, optimal_k)   
        km = KMeans(n_clusters=optimal_k, random_state=42)
        km_labels = km.fit_predict(X)
        articles.loc[group.index, "cluster_id"] = km_labels


    for (team_id, week_start, week_end, cluster_id), group in articles.groupby(["team_id", "week_start", "week_end", "cluster_id"]):
        
        # build the rows to upsert in cluster
        team_id = int(team_id) 
        cluster_id = int(cluster_id)
        size = int(len(group))

        cluster_rows.append(
            (team_id, week_start, week_end, cluster_id, size)
        )


        # --------
        # KEYWORDS
        # --------

        # Join all the texts in the group and eliminate numbers
        full_text = " ".join(group["full_text"].tolist())
        doc = nlp(full_text)
        tokens = [token.lemma_ for token in doc if not token.is_digit]
        cleaned_text = " ".join(tokens)
        doc = nlp(cleaned_text)

        # Extract named entities of type PERSON to extract key people
        people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        people = list(set(people))  
        cleaned_people = []
        for person in people: 
            cleaned_people.append(person.lower())

        # Extract general keywords using KeyBERT
        general_kws = kw_model.extract_keywords(
            cleaned_text,
            keyphrase_ngram_range=(1, 2), 
            stop_words='english',
            top_n=10
        )

        # Extract keywords related to key people using KeyBERT
        people_kws = kw_model.extract_keywords(
            cleaned_text, 
            keyphrase_ngram_range=(1, 3), 
            candidates=cleaned_people, 
            top_n=10
        )

        # Compile a regex pattern for the team's aliases
        alias_re = re.compile(TEAM_ALIASES.get(team_id, r"$^"), flags=re.IGNORECASE)
        # Filter and deduplicate the keywords
        merged_kws = general_kws + people_kws
        final_kws = filter_and_dedup(merged_kws, alias_re)

        # build the rows to upsert in keywords
        for kw, score in final_kws: 
            keyword_rows.append(
                (team_id, week_start, week_end, cluster_id, kw, score)
            )

        logger.info("Team %s week %s: n_keywords=%d", team_id, week_start, len(final_kws))


    # build the rows to upsert in topic
    for i, row in enumerate(articles.itertuples(index=False)):
        article_id = int(row.article_id)
        team_id = int(row.team_id) 
        week_start = row.week_start   
        week_end = row.week_end
        cluster_id = int(row.cluster_id)

        topic_rows.append(
            (team_id, week_start, week_end, article_id, cluster_id) 
        )


    # Write to DB in a transaction
    try:
        logger.info("Upserting %d clusters, %d keywords, %d topic rows",
                    len(cluster_rows), len(keyword_rows), len(topic_rows))
        cursor.execute("START TRANSACTION;")
        if cluster_rows:
            cursor.executemany(UPSERT_WEEKLY_CLUSTERS, cluster_rows)
        if keyword_rows:
            cursor.executemany(UPSERT_WEEKLY_KEYWORDS, keyword_rows)
        if topic_rows:
            cursor.executemany(UPSERT_WEEKLY_TOPICS, topic_rows)
        con.commit()
        logger.info("DB commit successful.")
    except Exception as e:
        con.rollback()
        logger.exception("DB write error, rolled back: %s", e)
        raise
    finally:
        cursor.close()
        con.close()



if __name__ == "__main__": 
    main()



