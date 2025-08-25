# ⚽ Footy Narratives

> Automated weekly storylines and topic summaries for the “Big Six” English clubs — end-to-end scraping, NLP/ML pipelines and a Streamlit dashboard to explore storylines, keywords and topic trends over time.

- **Live demo →** https://javiermascarena-footy-narratives-appstreamlit-app-h2n8ka.streamlit.app/
- **Code →** https://github.com/javiermascarena/footy-narratives

---

## 📌 TL;DR
Footy Narratives collects daily news about Arsenal, Chelsea, Liverpool, Manchester City, Manchester United and Tottenham. It automatically:

- classifies articles into **topics** (7 classes),
- groups articles into **weekly storylines (clusters)** per team,
- extracts **keywords** and **person names** for each cluster,
- exposes the results via a fast **Streamlit** web app with CSV downloads and historical topic trends.

The repo contains scrapers, ML notebooks, production-ready pipelines, DB migrations, and the Streamlit app.

---

## 📁 Repo layout (high level)

├─ app/

│ ├─ streamlit_app.py # Streamlit front-end

│ ├─ pipeline/ # production scripts (classify, cluster, keywords, upserts)

│ ├─ schema/ # SQL migrations & schema

│ └─ static/ # team logos, images

├─ notebooks/ # EDA, model training & evaluation

├─ scraper/ # scraping / ingestion code

├─ .github/workflows/ # scheduled scrape + pipeline workflows

├─ requirements.txt # main deps for the app

├─ requirements_ml_pipeline.txt # deps for ML pipelines (embeddings, KeyBERT, spacy, etc.)

├─ requirements_daily_scrape.txt # deps for scraping pipeline

└─ docker-compose.yml # local dev MySQL

---

## ✨ Project highlights
- **End-to-end engineering:** scheduled scraping → ingest → ML → dashboard.
- **Hybrid ML:** SBERT embeddings, KeyBERT for keywords, spaCy NER, KMeans clustering, supervised topic classification (~80% validation accuracy).
- **Normalized DB schema:** supports articles that reference multiple teams via `article_teams`.
- **Production-ready:** Docker for local dev, migration SQL, GitHub Actions for scheduling, Aiven MySQL for production, Streamlit deployment for the UI.

---

## 🧠 ML & technical summary

- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2).
- **Keyword extraction**: KeyBERT (distilbert variant) + spaCy (en_core_web_sm) for PERSON extraction.
- **Clustering**: KMeans per (team, week) with an elbow + distance heuristic to pick k; features = SBERT embeddings ± one-hot topic encoding.
- **Topic classifier**: SBERT embeddings → sklearn pipeline (StandardScaler + LogisticRegression). Model persisted with joblib.
- **Performance**: classifier achieved ~80% overall accuracy on the validation set used during development.

See notebooks/ for experiments, training code and evaluation outputs.  

--- 

## 🗄️ Database design (high-level)

- **articles** — raw article records
- **article_teams** — many-to-many mapping (article may mention multiple teams)
- **weekly_topic** — per (team, week, article): cluster_id, topic_id, topic_probability
- **weekly_clusters** — per (team, week, cluster) metadata
- **weekly_keywords** — keywords and scores per cluster

Migrations are in app/schema/migrations. Always back up before applying to production data.

---

## ☁️ Deployment & scheduling (production notes)

- **DB (prod)**: Aiven MySQL.
- **Scheduling**: GitHub Actions for daily scrapes and weekly pipelines (cron + manual trigger).
- **App host**: Streamlit Community Cloud.

---

## 🧾 License & contact

- **License**: [MIT](./LICENSE)
- **Author**: Javier Mascareña — <javiermascarenagonzalez@gmail.com> — https://www.linkedin.com/in/javier-mascare%C3%B1a-gonz%C3%A1lez-a6a040331/
