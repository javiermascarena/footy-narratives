import pandas as pd
import os
import re



script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "..", "data", "raw", "articles.csv")
articles = pd.read_csv(csv_path)

for article in articles.itertuples(): 
    teams = article.Teams.split(", ")
    team_list = []
    for team in teams: 
        team = team.replace("'", "")
        team = team.replace("[", "")
        team = team.replace("]", "")
        team_list.append(team)

    print(team_list)
