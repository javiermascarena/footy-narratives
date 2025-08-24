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
    author = soup.find(class_="sdc-article-author__name")
    if author:
        author = author.text.strip()
    else: 
        author = ""

    # Find the article body in the HTML content
    # If the article body is not found, return an empty string
    article = soup.find(class_="sdc-article-body sdc-article-body--lead")
    html_text = article.find_all("p", recursive=False)
    cleaned_text = ""
    for paragraph in html_text: 
        cleaned_text += paragraph.text.strip() + "\n" 

    return (cleaned_text, author)


def sky_scraper(lower_time, upper_time) -> pd.DataFrame:
    """
    Scrapes the SkySports Football RSS feed for articles related to mens football within a specified time range.
    The articles are filtered based on the presence of specific team names in the title or summary.
    The scraped articles are stored in a DataFrame.
    """

    # URL of the SkySports RSS feed to parse
    url = "https://www.skysports.com/rss/11095"

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

        # Check if the post's published date is within the specified range, has the tag "News Story" or "Article/Blog",
        # has teams, and is not already in the previous data
        if new_comparison_time >= lower_time \
            and new_comparison_time <= upper_time \
            and post.tags[0].term in ("News Story", "Article/Blog") \
            and teams:

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
                "Outlet": "SkySports"
            }
            # Concatenate the new post to the DataFrame
            new_data = pd.concat([new_data, pd.DataFrame([post])], ignore_index=True)

    return new_data

