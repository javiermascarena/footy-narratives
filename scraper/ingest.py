import mysql.connector 
import pandas as pd
import os
from datetime import datetime



db = mysql.connector.connect(
    host = "localhost",
    port = 3306,
    user = "appuser", 
    password = "appuserpass",
    database = "footy_narratives"
)

mycursor = db.cursor()

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "..", "data", "raw", "articles.csv")
articles = pd.read_csv(csv_path)
date_format = "%a, %d %b %Y %H:%M:%S"

for article in articles.itertuples(): 
    title = article.Title
    summary = article.Summary
    link = article.Link
    date = datetime.strptime(article.Date, date_format)
    full_text = article.Article
    raw_author = article.Author
    author = None if (pd.isna(raw_author) or raw_author=="") else raw_author
    outlet = article.Outlet
    raw = article.Teams
    teams = article.Teams.split(", ")
    team_list = []
    for team in teams: 
        team = team.replace("'", "")
        team = team.replace("[", "")
        team = team.replace("]", "")
        team_list.append(team)



    mycursor.execute("INSERT INTO outlets (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = name", (outlet,))
    mycursor.execute("SELECT id FROM outlets WHERE name = %s", (outlet,))
    outlet_id = mycursor.fetchone()[0]

    if author: 
        mycursor.execute("INSERT INTO authors (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = name", (author,))
        mycursor.execute("SELECT id FROM authors WHERE name = %s", (author,))
        author_id = mycursor.fetchone()[0]
    else:
        author_id = None

    team_ids = []
    for team in team_list: 
        mycursor.execute("INSERT INTO teams (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = name", (team,))
        mycursor.execute("SELECT id FROM teams WHERE name = %s", (team,))
        team_ids.append(mycursor.fetchone()[0])


    mycursor.execute("INSERT INTO articles (link, title, summary, publication_date, outlet_id, author_id, full_text) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                        "ON DUPLICATE KEY UPDATE title = VALUES(title), summary = VALUES(summary), full_text = VALUES(full_text)",
                     (link, title, summary, date, outlet_id, author_id, full_text))
    mycursor.execute("SELECT id FROM articles WHERE link = %s", (link,))
    article_id = mycursor.fetchone()[0]

    for team_id in team_ids: 
        mycursor.execute("INSERT INTO article_teams (article_id, team_id) VALUES (%s, %s)", (article_id, team_id))

db.commit()
db.close()