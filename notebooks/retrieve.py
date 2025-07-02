import mysql.connector
import pandas as pd
import re
import os

if __name__ == "__main__":
    # Connect to the MySQL database
    db = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="appuser",
        password="appuserpass",
        database="footy_narratives"
    )

    # Create a cursor to execute SQL queries
    mycursor = db.cursor(buffered=True)

    # Query to retrieve all articles from the database
    query = "SELECT article_id, full_text, team_id, outlet_id " \
    "FROM article_teams " \
    "INNER JOIN articles ON articles.id=article_teams.article_id " \
    "ORDER BY publication_date DESC LIMIT 50"
    mycursor.execute(query)

    # Fetch all results and convert them to a DataFrame
    articles = pd.DataFrame(mycursor.fetchall(), columns=[i[0] for i in mycursor.description])

    # Close the cursor and database connection
    mycursor.close()
    db.close()

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
    teams = {"Arsenal": "Arsenal|Gunners",
              "Chelsea": "Chelsea|Blues",
              "Manchester United": "Manchester United|Man Utd|Red Devils|Man United",
              "Liverpool": "Liverpool|Reds",
              "Manchester City": "Manchester City|Man City|Citizens",
              "Tottenham Hotspur": "Tottenham Hotspur|Spurs|Tottenham"}
    
    # Create a list to hold all rows of the sentences DataFrame
    all_rows = []
    # Iterate through each article and split the full text into sentences
    for _, row in articles.iterrows():
        # Split the full text into sentences using regex to handle punctuation
        sentences = re.split(r'(?<=[.?!])"?\s+', row.full_text)
        current_team = None  # Track the current team mentioned in the sentences

        # Iterate through each sentence to find teams mentioned
        for sent in sentences:
            # Clean the sentence by removing extra whitespace
            sent_clean = re.sub(r"\s+", " ", sent).strip()
            # Skip empty sentences
            if not sent_clean:
                continue

            # Find all teams mentioned in this sentence
            found = []
            for team in teams: 
                alias = teams[team]
                pattern = r"\b(" + alias + r")\b"
                if re.search(pattern, sent_clean, re.IGNORECASE):
                    found.append(team)

            # If no team is found, update the current team
            if len(found) > 0:
                current_team = found

            # If a team is found, append the sentence and team information to the list
            if current_team and len(current_team) == 1: 
                # if you want to drop sentences with no team ever seen, check current_team is not None
                all_rows.append({
                    "Sentence":    sent_clean,
                    "Article id":  row.article_id,
                    "Outlet":      outlet_id_map[row.outlet_id],
                    "Team":        current_team[0],
                    "Positiveness": None
                })

            # If multiple teams are found, append each team separately
            elif current_team and len(current_team) > 1:
                for team in current_team: 
                    # if you want to drop sentences with no team ever seen, check current_team is not None
                    all_rows.append({
                        "Sentence":    sent_clean,
                        "Article id":  row.article_id,
                        "Outlet":      outlet_id_map[row.outlet_id],
                        "Team":        team,
                        "Positiveness": None
                    })
                # Update the current team to the team of the article
                current_team = [team_id_map[row.team_id]]
            
            # If no team is found, append the sentence with None for team
            else: 
                all_rows.append({
                        "Sentence":    sent_clean,
                        "Article id":  row.article_id,
                        "Outlet":      outlet_id_map[row.outlet_id],
                        "Team":        None,
                        "Positiveness": None
                    })

    # Create a DataFrame from the list of rows
    sentences_df = pd.DataFrame(all_rows, columns=[
        "Sentence", "Article id", "Outlet", "Team", "Positiveness"
    ])
    # Fill missing team names by backfilling within each article
    sentences_df['Team'] = (
        sentences_df
        .groupby('Article id')['Team']
        .transform('bfill')
    )

    # Save the DataFrame to a CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "labeled_sentences.csv")
    sentences_df.to_csv(csv_path, index=False)
    