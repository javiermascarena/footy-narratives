import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name
import requests
from bs4 import BeautifulSoup
from typing import Tuple


def get_details_from_url(url) -> Tuple[str, str]:
    """
    Extracts the article text and authors from a given URL. 
    Args:
        url (str): The URL of the article to be processed.
    Returns:
        Tuple[str, str]: A tuple containing the cleaned article text and the author's name.
    """
    # Send a GET request to the URL
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    # Find the author name in the HTML content
    # If the author is not found, return an empty string
    try: 
        author = soup.find("div", attrs={"data-component": "byline-block"}).find(class_="ssrcss-12jkbjf-Text-TextContributorName e19uhciu6")
        author = author.text.strip()
    except AttributeError:
        author = ""

    # Find the text blocks in the HTML content
    text_blocks = soup.find_all("div", attrs={"data-component": ["text-block","subheadline-block"]})

    # If the article body is not found, return an empty string
    cleaned_text = ""
    # Iterate through the text blocks and extract the text from paragraphs and headings
    for block in text_blocks:
        html_text = block.find_all(["p", "h2"])
        for paragraph in html_text: 
            cleaned_text += paragraph.text.strip() + "\n" 
    
    return (cleaned_text, author)


def check_mens_football(url) -> bool:
    """
    Checks if the post is related to womens football.
    Args:
        url (str): The URL of the article to be checked.    
    Returns:
        bool: True if the post is related to mens football, False otherwise.
    """
    # Send a GET request to the URL
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    # Check if the womens football section is present in the HTML content
    womens_football = soup.find("a", attrs={"href": "/sport/football/womens"})
    if womens_football:
        return False
    else: 
        return True


def bbc_scraper(lower_time, upper_time) -> pd.DataFrame:
    """
    Scrapes the BBC Sport Football RSS feed for articles related to mens football within a specified time range.
    The articles are filtered based on the presence of specific team names in the title or summary.
    The scraped articles are stored in a DataFrame.
    """

    # URL of the BBC RSS feed to parse
    url = "https://feeds.bbci.co.uk/sport/football/rss.xml"

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

            # Check if the post is related to mens football
            mens_football = check_mens_football(post.link)
            # If the post is not related to mens football, skip it
            if not mens_football:
                continue

            # Get the article text and author from the URL
            article, author = get_details_from_url(post.link)

            # Skip if no article text is found
            if article == "" or "WSL" in article: 
                continue  

            # Append the post details to the DataFrame
            post = {
                "Title": post.title,
                "Summary": post.summary,
                "Link": post.link,
                "Date": new_comparison_time.strftime(news_format),
                "Author": author,
                "Teams": teams,
                "Article": article, 
                "Outlet": "BBC"
            }
            new_data = pd.concat([new_data, pd.DataFrame([post])], ignore_index=True)

    return new_data

    