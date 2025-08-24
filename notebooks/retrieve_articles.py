import pandas as pd
import re
import os
from app.db import get_conn  # connection with Aiven DB

def get_teams_from_article(row, teams, team_id_map) -> list:
    """
    Extracts the teams mentioned in the article's full text.
    Args:
        row (pd.Series): A row from the DataFrame containing article data.
        teams (dict): A dictionary mapping team names to their aliases.
        team_id_map (dict): A dictionary mapping team IDs to their names.
    Returns:
        list: A list of teams mentioned in the article.
    """
    
    teams_article = []
        
    # Count the occurrences of each team in the article's full text
    counts = {team: 0 for team in teams}
    for team in teams:
        alias = teams[team] 
        pattern = re.compile(r"\b("+alias+r")\b", re.IGNORECASE)
        matches = pattern.findall(row.full_text)
        counts[team] = len(matches)

    # Append the team with the most mentions to the teams_article list
    most_counted_team = max(counts, key=counts.get)
    teams_article.append(most_counted_team)
    # if the team was mentioned at least 5 times, we add it to the list
    for team, count in counts.items():
        if count >= 5 and team not in teams_article:
            teams_article.append(team)

    # If no teams were found, if there was only one team_id in the article,
    # we set this team_id as the only team in the article
    if teams_article == [] and len(row.team_id) == 1:
        teams_article = [team_id_map[row.team_id[0]]]

    return teams_article


if __name__ == "__main__":
    # Connect to the MySQL database
    conn = get_conn()

    # Create a cursor to execute SQL queries
    mycursor = conn.cursor(buffered=True)

    # Query to retrieve all articles from the database
    query = "SELECT article_id, full_text, team_id, outlet_id, publication_date, title " \
    "FROM article_teams " \
    "INNER JOIN articles ON articles.id=article_teams.article_id " \
    "ORDER BY publication_date DESC"
    mycursor.execute(query)

    # Fetch all results and convert them to a DataFrame
    rows = mycursor.fetchall()
    columns = [i[0] for i in mycursor.description]
    articles_raw = pd.DataFrame(rows, columns=columns)

    # Group by article_id and aggregate team_ids into a list
    articles = articles_raw.groupby(
        ["article_id", "full_text", "outlet_id", "publication_date", "title"], as_index=False
    ).agg({"team_id": lambda x: list(set(x))})

    # Close the cursor and database connection
    mycursor.close()
    conn.close()

    # Define mappings for team and outlet IDs to names
    team_id_map = {1: "Arsenal", 
                2: "Chelsea",
                3: "Liverpool",
                4: "Manchester City",
                5: "Manchester United",
                6: "Tottenham Hotspur"}
    outlet_id_map = {1: "BBC",
                    2: "TheGuardian",    
                    3: "SkySports"}
    
    # Define the teams and their aliases
    # This is a dictionary where the key is the team name and the value is a regex
    teams = {"Arsenal": "Arsenal|Gunners|Emirates",
             "Chelsea": "Chelsea|Blues|Stamford Bridge",
             "Manchester United": "Manchester United|Man Utd|Red Devils|Man United|Old Trafford|United",
             "Liverpool": "Liverpool|Reds|Anfield",
             "Manchester City": "Manchester City|Man City|Citizens|Etihad|Guardiola|City",
             "Tottenham Hotspur": "Tottenham Hotspur|Spurs|Tottenham|White Hart Lane"}
    
    # Create a list to hold all rows of the sentences DataFrame
    all_rows = []
    # Iterate through each article and split the full text into paragraphs
    for _, row in articles.iterrows():

        # Skip women's football articles if they mention women at least 5 times
        pattern = re.compile(r"\b("+"women"+r")\b", re.IGNORECASE)
        matches = pattern.findall(row.full_text)
        count = len(matches)
        if count >= 5:
            continue

        # Get the teams mentioned in the article
        teams_article = get_teams_from_article(row, teams, team_id_map)
            
        # Now we create a row for the combination of paragraph and team
        for team in teams_article: 
            all_rows.append({
                "Full_text":   row.full_text,
                "Article_ID":  row.article_id,
                "Outlet":      outlet_id_map[row.outlet_id],
                "Date":        row.publication_date,
                "Team":        team, 
                "Title":       row.title
            })


    # Create a DataFrame from the list of rows
    sentences_df = pd.DataFrame(all_rows, columns=[
        "Full_text", "Article_ID", "Outlet", "Date", "Team", "Title"
    ])

    # Save the DataFrame to a CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "articles.csv")
    sentences_df.to_csv(csv_path, index=False)
    