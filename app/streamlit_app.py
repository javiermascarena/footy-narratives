import streamlit as st
from pathlib import Path
import pandas as pd
import datetime
import altair as alt
import io
from streamlit.components.v1 import html as st_html

# ---- CONFIG ----
st.set_page_config(page_title="⚽ Footy Narratives", layout="wide", initial_sidebar_state="expanded")

# Mapping topics to IDs and colors
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

# Map each team to its image path
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
    # small pill badge using inline CSS 
    return f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{color_hex};color:white;font-weight:600;font-size:12px;margin-right:6px">{label}</span>'


def df_from_query_result(qr):
    # return the result of conn.query into a DataFrame
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

# ---- DB CONNECTION ----
conn = st.connection('mysql', type='sql')

# ---- SIDEBAR: explanation + filters ----
st.sidebar.title("Filters & Info")
st.sidebar.markdown("""
:grey-background[What this does:] groups news into **weekly storylines** (clusters) per team — a short **set of articles** about the same event (e.g., a transfer or injury).

:grey-background[How to read:] choose team & week → see the **main storylines** with a few keywords and representative articles.

:grey-background[Powered by ML:] storylines, keywords and topic labels are produced automatically using **machine learning** (BERT embeddings + other techniques). These are summaries to help exploration, not definitive facts.
""")

# Week selector: pick a date and compute week start/end
day = st.sidebar.date_input("Select week (any day within the week)", value=datetime.date.today())
week_start = day - datetime.timedelta(days=day.weekday())
week_end = week_start + datetime.timedelta(days=6)

# Team selector: dropdown with team names
team = st.sidebar.selectbox("Select team", list(TEAM_IMAGES.keys()), index=0)

# Topic filter: multiselect to filter by topic
topic_filter = st.sidebar.multiselect("Filter by topic", options=list(TOPICS_MAPPING.values()))

# Weeks back slider for trends
weeks_back = st.sidebar.slider("Weeks to show in trends", min_value=4, max_value=52, value=12, step=1)

# ---- HEADER ----
col1, col2 = st.columns([0.12, 0.88])
with col1:
    team_image_path = TEAM_IMAGES.get(team)
    if team_image_path and team_image_path.exists():
        st.image(team_image_path, width=90)
with col2:
    st.title("⚽ Footy Narratives")
    st.write(f"**{team} — {week_start.isoformat()} → {week_end.isoformat()}**")
    st.write("The week's main storylines, with short keywords and a top article.")
    st.caption("Storylines, keywords and topic labels are generated using AI to summarize articles — use as a guide.")

st.divider()

# ---- QUERY: articles + cluster keywords ----
@st.cache_data(show_spinner=False)  # cache data for performance
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


@st.cache_data(show_spinner=False)  # cache keywords loading
def load_cluster_keywords(team_name: str, week_start_iso: str, week_end_iso: str):
    # The query returns keywords as "keyword:score,keyword2:score2,..." per cluster_id
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


# ---- LOAD DATA ----
articles = load_week_data(team, week_start.isoformat(), week_end.isoformat())
cluster_kw_df = load_cluster_keywords(team, week_start.isoformat(), week_end.isoformat())

# no articles found
if articles.empty:
    st.warning("No articles found for this team/week. Try another week.")
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
m2.metric("Storylines", num_clusters)
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

# ensure consistent order & colors using the mappings
domain = [TOPICS_MAPPING[i] for i in sorted(TOPICS_MAPPING.keys())]
range_colors = [COLOR_FOR_TOPIC[i] for i in sorted(COLOR_FOR_TOPIC.keys())]

# Create a bar chart for topic counts
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
st.write("The number of articles per topic this week.")
st.altair_chart(chart, use_container_width=True)


# ---- TOPIC TRENDS (history) ----
st.subheader("Topic trends over time")
st.write("Each line shows the share of articles for a topic in each recorded week.")

@st.cache_data(show_spinner=False)
def load_trends(team_name: str):
    q = """
    SELECT wt.week_start, wt.topic_id, COUNT(*) AS cnt
    FROM weekly_topic wt
    JOIN teams t ON wt.team_id = t.id
    WHERE t.name = :team
    GROUP BY wt.week_start, wt.topic_id
    ORDER BY wt.week_start ASC;
    """
    params = {"team": team_name}
    res = conn.query(q, params=params)
    df_tr = df_from_query_result(res)
    if df_tr.empty:
        return df_tr
    df_tr["week_start"] = pd.to_datetime(df_tr["week_start"]).dt.date
    return df_tr

trends_df = load_trends(team)

if not trends_df.empty:
    # filter out weeks before June 1, 2025 and after the selected week_end
    lower_cutoff = datetime.date(2025, 6, 1)
    upper_cutoff = week_end
    trends_df = trends_df[(trends_df["week_start"] >= lower_cutoff) & (trends_df["week_start"] <= upper_cutoff)]

    # compute percentage per week
    total_per_week = trends_df.groupby("week_start")["cnt"].sum().rename("total").reset_index()
    trends_df = trends_df.merge(total_per_week, on="week_start")
    trends_df["pct"] = trends_df["cnt"] / trends_df["total"] * 100
    # map topic names
    trends_df["topic"] = trends_df["topic_id"].map(TOPICS_MAPPING)
    # limit to last N weeks selected by the user
    trends_df = trends_df.sort_values("week_start")
    unique_weeks = sorted(trends_df["week_start"].unique())
    last_weeks = unique_weeks[-weeks_back:]
    trends_df = trends_df[trends_df["week_start"].isin(last_weeks)]

    domain = [TOPICS_MAPPING[i] for i in sorted(TOPICS_MAPPING.keys())]
    range_colors = [COLOR_FOR_TOPIC[i] for i in sorted(COLOR_FOR_TOPIC.keys())]

    # Create a line chart for trends
    chart_trends = (
        alt.Chart(trends_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("week_start:T", title="Week"),
            y=alt.Y("pct:Q", title="% of weekly articles"),
            color=alt.Color("topic:N", scale=alt.Scale(domain=domain, range=range_colors)),
            tooltip=["week_start", "topic", alt.Tooltip("pct", format=".1f")]
        )
        .properties(height=300)
    )
    st.altair_chart(chart_trends, use_container_width=True)
else:
    st.info("Not enough historical data to plot topic trends for this team.")

st.divider()

# ---- CLUSTER CARDS ----
st.subheader("Storylines")
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
                    s = abs(float(score))  # ensure score is in absolut value
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
    # take first 5 (normal kws) and middle 5 (people kws) for display
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
    # create chips for keywords with size based on normalized score
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
     # Display cluster header with topic badge, keywords and top article
    with cols[0]:
        st.markdown(f"### Storyline {cluster_id+1} — {count} articles")
        st.markdown(topic_badge_html(topic_name, COLOR_FOR_TOPIC.get(topic_id, "#666")), unsafe_allow_html=True)

        if chips:
            st.caption("Top keywords: chip size = strength")
            chips_html = " ".join(chips)
            st.markdown(chips_html, unsafe_allow_html=True)

        st.markdown(f"**Top article:** [{top_article_row['title']}]({top_article_row['link']}) — {top_article_row['outlet_name']} ({top_article_row['publication_date']})")

    # Download button for cluster CSV
    with cols[1]:
        cluster_df = group[["title","link","publication_date","outlet_name","topic_id","keywords"]].copy()
        csv = cluster_df.to_csv(index=False).encode("utf-16")
        st.download_button(label="Download CSV", data=csv, file_name=f"cluster_{cluster_id+1}.csv", mime="text/csv")

    # Show all articles in the cluster
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
st.caption("Data powered by the scraping and ML pipeline.")

# full table + download
st.subheader("All articles (table)")
st.dataframe(df[["cluster_id","topic_id","title","publication_date","outlet_name","keywords"]].rename(columns={"topic_id":"topic"}))

full_csv = df.to_csv(index=False).encode("utf-16")
st.download_button("Download full week CSV", data=full_csv, file_name=f"{team}_{week_start.isoformat()}_{week_end.isoformat()}.csv", mime="text/csv")
