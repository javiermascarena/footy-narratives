import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name
import os
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
    article = soup.find(class_="article-body-commercial-selector article-body-viewer-selector dcr-11jq3zt").find_all(["p", "h2"])
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


if __name__ == "__main__":
    # URL of The Guardian RSS feed to parse
    url = "https://www.theguardian.com/football/rss"

    # Parse the RSS feed and store the results
    newsfeed = feedparser.parse(url)
    posts = newsfeed.entries

    # Define the lower and upper date boundaries as strings
    lower_time_bound = "2025-05-01"
    upper_time_bound = "2026-06-30"
    # Define the format for the boundaries and convert strings to datetime 
    common_format = "%Y-%m-%d"
    lower_comparison_time = datetime.strptime(lower_time_bound, common_format)
    upper_comparison_time = datetime.strptime(upper_time_bound, common_format)

    # Define the format for the published date in the RSS feed entries
    news_format = "%a, %d %b %Y %H:%M:%S"

    # Create an empty DataFrame to store the results
    new_data = pd.DataFrame(columns=["Title", "Summary", "Link", "Date", "Author", "Teams", "Article"])

    # Load the previous data from the CSV file if it exists
    # If the file does not exist, create a new DataFrame
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "raw", "theguardian-articles.csv")
    empty_file = False
    try: 
        previous_data = pd.read_csv(csv_path)
    except FileNotFoundError: 
        previous_data = new_data
        empty_file = True

    # Iterate over each post in the RSS feed
    for post in posts: 
        # Convert the published date to a datetime object removing the BST part
        date_without_bst = " ".join(post.published.split(" ")[:-1])
        new_comparison_time = datetime.strptime(date_without_bst, news_format)

        # Extract team names from title and summary
        teams = get_team_name(post.title + " " + post.summary)  

        # Check if the post's published date is within the specified range,
        # has the desired teams, and is not already in the previous data
        if new_comparison_time >= lower_comparison_time \
            and new_comparison_time <= upper_comparison_time \
            and teams \
            and (not previous_data["Link"].isin([post.link]).any() or empty_file):

            print(post.link)
            # Get the article text and author from the URL
            article, author, summary = get_details_from_url(post.link)

            # Append the post details to the DataFrame
            post = {
                "Title": post.title,
                "Summary": summary,
                "Link": post.link,
                "Date": new_comparison_time.strftime(news_format),
                "Author": author,
                "Teams": teams,
                "Article": article
            }
            new_data = pd.concat([new_data, pd.DataFrame([post])], ignore_index=True)

    # Append the new data to the CSV file if it is not empty, otherwise create a new CSV file
    if not empty_file: 
        new_data.to_csv(csv_path, mode="a", index=False, header=False)
    else: 
        new_data.to_csv(csv_path, index=False)
