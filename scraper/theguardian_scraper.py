import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name
import requests
from bs4 import BeautifulSoup   
from typing import Tuple


def get_details_from_url(url) -> Tuple[str, str, str]:
    """
    Extracts the article text and authors from a given URL. 
    Args:
        url (str): The URL of the article to be processed.
    Returns:
        Tuple[str, str, str]: A tuple containing the cleaned article text, the author's name and the subtitle.
    """
    # Send a GET request to the URL
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    # Find the author name in the HTML content
    author = soup.find("a", attrs={"rel":"author"})
    if not author: 
        author = soup.find("a", attrs={"data-component": "section"}).find("span")
    author = author.text.strip() if author else ""

    # Find the subtitle in the HTML content
    subtitle = soup.find("div", attrs={"data-gu-name": "standfirst"}).find("p")
    subtitle = subtitle.text.strip() if subtitle else ""

    # Find the article body in the HTML content
    try: 
        article = soup.find(class_="article-body-commercial-selector article-body-viewer-selector dcr-11jq3zt").find_all(["p", "h2"])
    except AttributeError:
        return ("", author, subtitle)

    cleaned_text = ""   
    promotion_texts = ["Sign up to Football Daily", 
                       "Kick off your evenings with the Guardian's take on the world of football", 
                       "after newsletter promotion"]
    # Clean the article text by removing promotional texts
    # and concatenating the text from paragraphs and headings
    for paragraph in article: 
        if paragraph.text.strip() in promotion_texts:
            continue
        cleaned_text += paragraph.text.strip() + "\n"

    return (cleaned_text, author, subtitle)


def theguardian_scraper(lower_time, upper_time) -> pd.DataFrame:
    """ 
    Scrapes The Guardian Football RSS feed for articles related to mens football within a specified time range.
    The articles are filtered based on the presence of specific team names in the title or summary.
    The scraped articles are stored in a DataFrame.
    """

    # URL of The Guardian RSS feed to parse
    url = "https://www.theguardian.com/football/rss"

    # Parse the RSS feed and store the results
    newsfeed = feedparser.parse(url)
    posts = newsfeed.entries

    # Define the format for the published date in the RSS feed entries
    news_format = "%a, %d %b %Y %H:%M:%S"

    # Create an empty DataFrame to store the results
    new_data = pd.DataFrame(columns=["Title", "Summary", "Link", "Date", "Author", "Teams", "Article", "Outlet"])

    # Iterate over each post in the RSS feed
    for post in posts: 
        # Convert the published date to a datetime object removing the BST part
        date_without_bst = " ".join(post.published.split(" ")[:-1])
        new_comparison_time = datetime.strptime(date_without_bst, news_format)

        # Extract team names from title and summary
        teams = get_team_name(post.title + " " + post.summary)  

        # Check if the post's published date is within the specified range,
        # has the desired teams, and is not already in the previous data
        if new_comparison_time >= lower_time \
            and new_comparison_time <= upper_time \
            and teams:

            # Get the article text and author from the URL
            article, author, summary = get_details_from_url(post.link)
            # Skip if no article text is found
            if article == "" or "WSL" in article: 
                continue

            # Append the post details to the DataFrame
            post = {
                "Title": post.title,
                "Summary": summary,
                "Link": post.link,
                "Date": new_comparison_time.strftime(news_format),
                "Author": author,
                "Teams": teams,
                "Article": article, 
                "Outlet": "TheGuardian"
            }
            new_data = pd.concat([new_data, pd.DataFrame([post])], ignore_index=True)

    return new_data