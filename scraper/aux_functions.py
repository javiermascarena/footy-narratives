import re

def get_team_name(text) -> list: 
    """
    Extracts the team name from the text.
    This is a placeholder function and should be implemented based on specific requirements.
    """
    named_teams = []
    # Example implementation: return the first word as the team name
    teams = {"Arsenal": "Arsenal|Gunners",
              "Chelsea": "Chelsea|Blues",
              "Manchester United": "Manchester United|Man Utd|Red Devils|Man United|United",
              "Liverpool": "Liverpool|Reds",
              "Manchester City": "Manchester City|Man City|City|Citizens",
              "Tottenham Hotspur": "Tottenham Hotspur|Spurs|Tottenham"}
    
    # Iterate through the teams dictionary to find matches in the text
    for team in teams:
        alias = teams[team]
        # Create a regex pattern to match the team name or its aliases
        pattern = r"\b(" + alias + r")\b"
        if re.search(pattern, text, re.IGNORECASE):
            named_teams.append(team)    
    
    return named_teams