import streamlit as st
from pathlib import Path
import pandas as pd
import datetime
import altair as alt
import io

# ---- CONFIG ----
st.set_page_config(page_title="⚽ Footy Narratives", layout="wide", initial_sidebar_state="expanded")

# Replace these with the exact hex colors you like
TOPICS_MAPPING = {
    0: "transfers/rumours",
    1: "financial/club news",
    2: "controversies",
    3: "tactics/analysis",
    4: "editorial/opinion",
    5: "human-interest/player events",
    6: "other"
}
COLOR_FOR_TOPIC = {
    0: "#7C4DFF",  # purple
    1: "#1976D2",  # blue
    2: "#D32F2F",  # red
    3: "#FB8C00",  # orange
    4: "#FFC107",  # amber
    5: "#2E7D32",  # green
    6: "#9E9E9E",  # grey
}

BASE = Path.cwd() / "app" / "static"
TEAM_IMAGES = {
    "Arsenal": BASE / "Arsenal_FC.svg",
    "Chelsea": BASE / "Chelsea_FC.svg",
    "Liverpool": BASE / "Liverpool_FC.svg",
    "Manchester City": BASE / "Manchester_City_FC_badge.svg",
    "Manchester United": BASE / "Manchester_United_FC_crest.svg",
    "Tottenham Hotspur": BASE / "Tottenham_Hotspur.svg",
}

# ---- UTIL ----
def topic_badge_html(label: str, color_hex: str):
    # small pill badge using inline CSS (safe-ish)
    return f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{color_hex};color:white;font-weight:600;font-size:12px;margin-right:6px">{label}</span>'


def df_from_query_result(qr):
    # robustly turn the result of conn.query into a DataFrame
    if qr is None:
        return pd.DataFrame()
    if isinstance(qr, pd.DataFrame):
        return qr.copy()
    try:
        return pd.DataFrame(qr)
    except Exception:
        return pd.DataFrame(list(qr))


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert '#RRGGBB' or 'RRGGBB' to an rgba(...) string."""
    if not hex_color:
        return f"rgba(0,0,0,{alpha})"
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(0,0,0,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ---- DB CONNECTION (same as yours) ----
conn = st.connection('mysql', type='sql')

# ---- SIDEBAR: explain + filters ----
st.sidebar.title("Filters & Info")
st.sidebar.markdown("""
**What this does**  
Footy Narratives groups news articles into weekly clusters per team and shows the 10 most representative keywords for each cluster.  
**How to read**: pick a team + week → see cluster cards (top keywords + top article).  
""")

# Week selector: pick a date and compute week start/end
day = st.sidebar.date_input("Select week (any day within week)", value=datetime.date.today())
week_start = day - datetime.timedelta(days=day.weekday())
week_end = week_start + datetime.timedelta(days=6)

team = st.sidebar.selectbox("Select team", list(TEAM_IMAGES.keys()), index=0)

# Optional filters (topic filter we can show early)
topic_filter = st.sidebar.multiselect("Filter by topic", options=list(TOPICS_MAPPING.values()))

# ---- HEADER ----
col1, col2 = st.columns([0.12, 0.88])
with col1:
    team_image_path = TEAM_IMAGES.get(team)
    if team_image_path and team_image_path.exists():
        st.image(team_image_path, width=90)
with col2:
    st.title("⚽ Footy Narratives")
    st.write(f"**{team} — {week_start.isoformat()} → {week_end.isoformat()}**")
    st.write("Snapshot of the week's storylines, grouped by cluster. Click a cluster to explore articles and top keywords.")

st.divider()

# ---- QUERY: articles + cluster keywords ----
@st.cache_data(show_spinner=False)
def load_week_data(team_name: str, week_start_iso: str, week_end_iso: str):
    query = """
    SELECT wt.cluster_id, wt.topic_id, a.link, a.title, a.publication_date, o.name AS outlet_name
    FROM weekly_topic AS wt
    JOIN teams AS t ON wt.team_id = t.id
    JOIN articles AS a ON wt.article_id = a.id
    JOIN outlets AS o ON a.outlet_id = o.id
    WHERE t.name = :team
    AND wt.week_start = :week_start
    AND wt.week_end = :week_end;
    """
    params = {
        "team":           team_name,
        "week_start":     week_start_iso,
        "week_end":       week_end_iso
    }
    qr = conn.query(query, params=params)
    df = df_from_query_result(qr)
    # ensure datetimes
    if not df.empty:
        df["publication_date"] = pd.to_datetime(df["publication_date"]).dt.date
    return df


@st.cache_data(show_spinner=False)
def load_cluster_keywords(team_name: str, week_start_iso: str, week_end_iso: str):
    # This query returns keywords as "keyword:score,keyword2:score2,..." per cluster_id
    q = """
    SELECT wk.cluster_id,
        GROUP_CONCAT(CONCAT(wk.keyword, ':', wk.score) ORDER BY ABS(wk.score) DESC SEPARATOR ',') AS keywords
    FROM weekly_clusters AS wc
    JOIN weekly_keywords AS wk ON 
        wc.cluster_id = wk.cluster_id AND
        wc.week_start = wk.week_start AND 
        wc.week_end = wk.week_end AND 
        wc.team_id = wk.team_id
    JOIN teams AS t ON wk.team_id = t.id
    WHERE t.name = :team
      AND wc.week_start = :week_start
      AND wc.week_end = :week_end
    GROUP BY wk.cluster_id;
    """
    params = {"team": team_name, "week_start": week_start_iso, "week_end": week_end_iso}
    try:
        res = conn.query(q, params=params)
        return df_from_query_result(res)
    except Exception:
        return pd.DataFrame(columns=["cluster_id", "keywords"])


articles = load_week_data(team, week_start.isoformat(), week_end.isoformat())
cluster_kw_df = load_cluster_keywords(team, week_start.isoformat(), week_end.isoformat())

if articles.empty:
    st.warning("No articles found for this team/week. Try another week or check your ingestion.")
    st.stop()

# merge keywords (if available)
df = articles.copy()
if not cluster_kw_df.empty:
    df = df.merge(cluster_kw_df, on="cluster_id", how="left")  # adds 'keywords' column possibly NaN
else:
    df["keywords"] = ""

# helper to extract keyword list (without scores)
def extract_keyword_list(kstr):
    if not kstr or pd.isna(kstr):
        return []
    res = []
    for p in str(kstr).split(','):
        p = p.strip()
        if not p:
            continue
        res.append(p.split(':', 1)[0].strip())
    return res

# create keyword_list column for potential future use
df["keyword_list"] = df["keywords"].apply(extract_keyword_list)

# topic filter
if topic_filter:
    name_to_id = {v: k for k, v in TOPICS_MAPPING.items()}
    allowed_ids = [name_to_id[n] for n in topic_filter if n in name_to_id]
    df = df[df["topic_id"].isin(allowed_ids)]

# ---- METRICS ROW ----
num_articles = len(df)
num_clusters = df["cluster_id"].nunique()
dominant_topic_id = int(df["topic_id"].mode()[0]) if num_articles else None
dominant_topic_name = TOPICS_MAPPING.get(dominant_topic_id, "N/A") if dominant_topic_id is not None else "N/A"

m1, m2, m3 = st.columns([1,1,2])
m1.metric("Articles", num_articles)
m2.metric("Clusters", num_clusters)
with m3:
    if dominant_topic_id is not None:
        st.metric("Dominant topic", dominant_topic_name)
        st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
        st.markdown(topic_badge_html(dominant_topic_name, COLOR_FOR_TOPIC.get(dominant_topic_id, "#666")), unsafe_allow_html=True)
    else:
        st.metric("Dominant topic", "N/A")

st.divider()

# ---- TOPICS OVERVIEW CHART ----
topic_counts = df["topic_id"].map(TOPICS_MAPPING).value_counts().reset_index()
topic_counts.columns = ["topic", "count"]

# ensure consistent order & colors using your mappings
domain = [TOPICS_MAPPING[i] for i in sorted(TOPICS_MAPPING.keys())]
range_colors = [COLOR_FOR_TOPIC[i] for i in sorted(COLOR_FOR_TOPIC.keys())]

chart = (
    alt.Chart(topic_counts)
    .mark_bar()
    .encode(
        x=alt.X("count:Q", title="Article count"),
        y=alt.Y("topic:N", sort=domain, title=None),
        color=alt.Color(
            "topic:N",
            scale=alt.Scale(domain=domain, range=range_colors),
            legend=None
        ),
        tooltip=["topic", "count"]
    )
    .properties(height=300, width=700)
)

st.subheader("Topics Overview")
st.altair_chart(chart, use_container_width=True)

st.divider()

# ---- CLUSTER CARDS ----
st.subheader("Clusters")
clusters = df.groupby("cluster_id")
for cluster_id, group in clusters:
    count = len(group)
    top_article_row = group.sort_values("publication_date", ascending=False).iloc[0]
    topic_id = int(group["topic_id"].mode()[0])
    topic_name = TOPICS_MAPPING.get(topic_id, "Unknown")

    # obtain the aggregated keywords string for this cluster (if any)
    keywords_strs = group["keywords"].dropna().unique()
    if len(keywords_strs):
        kws = keywords_strs[0]
    else:
        kws = ""

    # parse into dict to deduplicate and keep max absolute score per keyword
    kw_scores = {}
    if kws:
        for item in kws.split(','):
            item = item.strip()
            if not item:
                continue
            if ':' in item:
                kw, score = item.rsplit(':', 1)
                try:
                    s = abs(float(score))
                except Exception:
                    s = 0.0
            else:
                kw = item
                s = 0.0
            k = kw.strip()
            if k in kw_scores:
                kw_scores[k] = max(kw_scores[k], s)
            else:
                kw_scores[k] = s

    # fallback if no numeric scores
    if not kw_scores and kws:
        for k in [x.strip() for x in kws.split(',') if x.strip()]:
            kw_scores[k] = 1.0

    # turn into sorted list
    parsed = sorted(kw_scores.items(), key=lambda x: x[1], reverse=True)
    mid_index = len(parsed) // 2
    best_keywords = parsed[:5] + parsed[mid_index:mid_index+5]

    # normalize scores to [0.4,1.0]
    scores = [s for _, s in best_keywords]
    if scores:
        min_s, max_s = min(scores), max(scores)
        if max_s == min_s:
            norms = [0.7 for _ in scores]
        else:
            norms = [(s - min_s) / (max_s - min_s) * 0.6 + 0.4 for s in scores]
    else:
        norms = []

    topic_color = COLOR_FOR_TOPIC.get(topic_id, "#666666")
    chips = []
    for (kw, s), norm in zip(best_keywords, norms):
        font_size = int(12 + (18 - 12) * norm)
        bar_w = int(20 + (80 - 20) * norm)
        chip_bg = hex_to_rgba("CCCCCC", 1.0)
        bar_color = hex_to_rgba(topic_color, 0.95)
        tooltip = f"{s:.2f}"
        chip_html = (
            f'<span title="{tooltip}" '
            f'style="display:inline-flex;align-items:center;gap:8px;padding:6px 10px;margin:3px;'
            f'border-radius:999px;background:{chip_bg};font-size:{font_size}px; color: #000000;">'
            f'  <span style="display:inline-block;width:{bar_w}px;height:8px;border-radius:4px;'
            f'background:{bar_color};"></span>'
            f'  <strong style="line-height:1; color: #000000;">{kw}</strong>'
            f'</span>'
        )

        chips.append(chip_html)

    cols = st.columns([0.88, 0.12])
    with cols[0]:
        st.markdown(f"### Cluster {cluster_id+1} — {count} articles")
        st.markdown(topic_badge_html(topic_name, COLOR_FOR_TOPIC.get(topic_id, "#666")), unsafe_allow_html=True)

        if chips:
            st.markdown('<div style="margin-top:6px;margin-bottom:6px;font-size:13px;color:#444">Top keywords (chip size = strength)</div>', unsafe_allow_html=True)
            chips_html = " ".join(chips)
            st.markdown(chips_html, unsafe_allow_html=True)

        st.markdown(f"**Top article:** [{top_article_row['title']}]({top_article_row['link']}) — {top_article_row['outlet_name']} ({top_article_row['publication_date']})")

    with cols[1]:
        cluster_df = group[["title","link","publication_date","outlet_name","topic_id","keywords"]].copy()
        csv = cluster_df.to_csv(index=False).encode("utf-8")
        st.download_button(label="Download CSV", data=csv, file_name=f"cluster_{cluster_id+1}.csv", mime="text/csv")

    with st.expander("Show all articles in cluster"):
        for _, row in group.sort_values("publication_date", ascending=False).iterrows():
            t = row["title"]
            l = row["link"]
            d = row["publication_date"]
            outlet = row["outlet_name"]
            topic_id_row = int(row["topic_id"])
            topic_html = topic_badge_html(TOPICS_MAPPING.get(topic_id_row, "Unknown"), COLOR_FOR_TOPIC.get(topic_id_row, "#666"))
            st.markdown(f"- [{t}]({l}) — {outlet} ({d})  ", unsafe_allow_html=True)
            st.markdown(topic_html, unsafe_allow_html=True)

    st.markdown("---")

# ---- FOOTER: export full week ----
st.caption("Data powered by your scrape + clustering pipeline. Add more UX improvements: search, sentiment, or a timeline view.")

# Optional: full table + download
st.subheader("All articles (table)")
st.dataframe(df[["cluster_id","topic_id","title","publication_date","outlet_name","keywords"]].rename(columns={"topic_id":"topic"}))

full_csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download full week CSV", data=full_csv, file_name=f"{team}_{week_start.isoformat()}_{week_end.isoformat()}.csv", mime="text/csv")
