import requests
from bs4 import BeautifulSoup
import feedparser


# URL of The Guardian RSS feed to parse
urls = ["https://www.theguardian.com/football/2025/jun/07/tottenham-ange-postecoglou-daniel-levy-europa-league", 
        "https://www.theguardian.com/football/2025/jun/13/football-transfer-rumours-alejandro-garnacho-manchester-united-aston-villa-victor-osimhen-bryan-mbeumo",
        "https://www.theguardian.com/football/2025/may/26/premier-league-2024-25-review-players-of-the-season"]

for url in urls: 
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    author = soup.find("a", attrs={"rel":"author"})
    if not author: 
        author = soup.find("a", attrs={"data-component": "section"}).find("span")
    author = author.text.strip() if author else ""

    subtitle = soup.find("div", attrs={"data-gu-name": "standfirst"}).find("p").text.strip()

    article = soup.find(class_="article-body-commercial-selector article-body-viewer-selector dcr-11jq3zt").find_all(["p", "h2"])
    cleaned_text = ""   
    promotion_texts = ["Sign up to Football Daily", 
                       "Kick off your evenings with the Guardian's take on the world of football", 
                       "after newsletter promotion"]
    for paragraph in article: 
        if paragraph.text.strip() in promotion_texts:
            continue
        cleaned_text += paragraph.text.strip() + "\n"



    print(f"Author: {author}")
    print(f"Subtitle: {subtitle}")
    print(f"Article: {cleaned_text}\n\n") 