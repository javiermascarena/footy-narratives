import mysql.connector 
import pandas as pd
import os
from datetime import datetime

if __name__ == "__main__":
    # Define the mappings for team and outlet IDs
    team_id_map = {"Arsenal": 1, 
                "Chelsea": 2,
                "Liverpool": 3,
                "Manchester City": 4,
                "Manchester United": 5,
                "Tottenham Hotspur": 6}
    outlet_id_map = {"BBC": 1,
                    "TheGuardian": 2,    
                    "SkySports": 3}

    # Connect to the MySQL database
    db = mysql.connector.connect(
        host = "localhost",
        port = 3306,
        user = "appuser", 
        password = "appuserpass",
        database = "footy_narratives"
    )

    # Create a cursor to execute SQL queries
    mycursor = db.cursor(buffered=True)

    # Get the current date and format it for the CSV file name
    current_date = datetime.now()
    file_date = current_date.strftime("%Y-%m-%d")
    file_date = f"{file_date}.csv"

    # Read the CSV file containing new articles
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "raw", "2025-07-30.csv")
    articles = pd.read_csv(csv_path, encoding='utf-16')
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
        outlet_id = outlet_id_map[outlet] 
        mycursor.execute("INSERT INTO outlets (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = name", (outlet_id, outlet))
        
        # Insert the author into the authors table, or update it if it already exists
        if author: 
            mycursor.execute("INSERT INTO authors (name) VALUES (%s) ON DUPLICATE KEY UPDATE name = name", (author,))
            mycursor.execute("SELECT id FROM authors WHERE name = %s", (author,))
            # Obtain the author ID for the newly inserted or updated author
            author_id = mycursor.fetchone()[0]
        else:
            author_id = None

        if pd.isna(summary): 
            summary = None

        # Insert the teams into the teams table, or update them if they already exist
        team_ids = []
        for team in team_list: 
            mycursor.execute("INSERT INTO teams (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = name", (team_id_map[team], team))
            team_ids.append(team_id_map[team])

        # Insert the article into the articles table, or update it if it already exists
        mycursor.execute("INSERT INTO articles (link, title, summary, publication_date, outlet_id, author_id, full_text) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                            "ON DUPLICATE KEY UPDATE title = VALUES(title), summary = VALUES(summary), full_text = VALUES(full_text)",
                        (link, title, summary, date, outlet_id, author_id, full_text))
        # Obtain the article ID for the newly inserted or updated article
        mycursor.execute("SELECT id FROM articles WHERE link = %s", (link,))
        article_id = mycursor.fetchone()[0]

        # Insert the article-team relationships into the article_teams table
        for team_id in team_ids: 
            mycursor.execute("INSERT IGNORE INTO article_teams (article_id, team_id) VALUES (%s, %s)", (article_id, team_id))

    # Commit the changes to the databases
    db.commit()
    db.close()