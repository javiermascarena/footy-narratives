import os
import sys
from datetime import datetime, timedelta
from bbc_scraper import bbc_scraper
from sky_scraper import sky_scraper
from theguardian_scraper import theguardian_scraper
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db import get_conn


if __name__ == "__main__":

    # Define the mappings for team and outlet IDs
    TEAM_ID_MAP = {"Arsenal": 1, 
                   "Chelsea": 2,
                   "Liverpool": 3,
                   "Manchester City": 4,
                   "Manchester United": 5,
                   "Tottenham Hotspur": 6}
    OUTLET_ID_MAP = {"BBC": 1,
                     "TheGuardian": 2,    
                     "SkySports": 3}

    # Get the current date and the last date (24 hours ago)
    # Since the script is run daily, we can use the current date and the last date
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    current_date = datetime.now()
    last_date = current_date - timedelta(days=1)

    # Scrape data from each source and combine the results
    sky_df = sky_scraper(last_date, current_date)
    bbc_df = bbc_scraper(last_date, current_date)
    theguardian_df = theguardian_scraper(last_date, current_date)
    articles = pd.concat([sky_df, bbc_df, theguardian_df], ignore_index=True)


    # Connect to the database
    timeout = 10
    conn = get_conn()   
    cur = conn.cursor()

    # Define the date format for parsing the publication date
    date_format = "%a, %d %b %Y %H:%M:%S"

    # Iterate over each article in the DataFrame
    for article in articles.itertuples(): 
        # Extract the relevant fields from the article
        title = article.Title
        summary = article.Summary
        link = article.Link
        # Parse the publication date from the string to a datetime object
        date = datetime.strptime(article.Date, date_format)
        full_text = article.Article
        raw_author = article.Author
        # Handle the case where the author is NaN or an empty string
        author = None if (pd.isna(raw_author) or raw_author=="") else raw_author
        outlet = article.Outlet
        # Clean the different team names from the Teams field
        raw = article.Teams
        teams = article.Teams.split(", ")
        team_list = []
        for team in teams: 
            team = team.replace("'", "")
            team = team.replace("[", "")
            team = team.replace("]", "")
            team_list.append(team)

        # Insert the outlet into the outlets table, or update it if it already exists
        outlet_id = OUTLET_ID_MAP[outlet] 
        cur.execute("INSERT INTO outlets (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = name", (outlet_id, outlet))
        
        # Insert the author into the authors table, or update it if it already exists
        if author: 
            cur.execute("INSERT INTO authors (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = name", (author,))
            cur.execute("SELECT id FROM authors WHERE name = %s", (author,))
            # Obtain the author ID for the newly inserted or updated author
            author_id = cur.fetchone()["id"]
        else:
            author_id = None

        if pd.isna(summary): 
            summary = None

        # Insert the teams into the teams table, or update them if they already exist
        team_ids = []
        for team in team_list: 
            cur.execute("INSERT INTO teams (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = name", (TEAM_ID_MAP[team], team))
            team_ids.append(TEAM_ID_MAP[team])

        # Insert the article into the articles table, or update it if it already exists
        cur.execute("INSERT INTO articles (link, title, summary, publication_date, outlet_id, author_id, full_text) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE title = VALUES(title), summary = VALUES(summary), full_text = VALUES(full_text)",
                    (link, title, summary, date, outlet_id, author_id, full_text))
        # Obtain the article ID for the newly inserted or updated article
        cur.execute("SELECT id FROM articles WHERE link = %s", (link,))
        article_id = cur.fetchone()["id"]

        # Insert the article-team relationships into the article_teams table
        for team_id in team_ids: 
            cur.execute("INSERT IGNORE INTO article_teams (article_id, team_id) VALUES (%s, %s)", (article_id, team_id))

    # Commit the changes to the databases
    conn.commit()
    conn.close()

    