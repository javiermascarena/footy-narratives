import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name
import requests
from bs4 import BeautifulSoup
from typing import Tuple
import os
import argparse


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


if __name__ == "__main__":
    
    # Parse command line arguments for lower and upper time bounds
    # This allows the script to be run with specific time bounds for appending articles
    parser = argparse.ArgumentParser()
    parser.add_argument("lower_time", help="Lower time bound for appending articles")
    parser.add_argument("upper_time", help="Upper time bound for appending articles")
    args = parser.parse_args()
    lower_time = args.lower_time
    upper_time = args.upper_time

    # Put the lower and upper time bounds into datetime objects
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    lower_comparison_time = datetime.strptime(lower_time, date_format)
    upper_comparison_time = datetime.strptime(upper_time, date_format)

    # URL of the SkySports RSS feed to parse
    url = "https://www.skysports.com/rss/11095"

    # Parse the RSS feed and store the results
    newsfeed = feedparser.parse(url)
    posts = newsfeed.entries 

    # Define the format for the published date in the RSS feed entries
    news_format = "%a, %d %b %Y %H:%M:%S"

    # Create an empty DataFrame to store the results
    new_data = pd.DataFrame(columns=["Title", "Summary", "Link", "Date", "Author", "Teams", "Article", "Outlet"])

    # Load the previous data from the CSV file if it exists
    # If the file does not exist, create a new DataFrame
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "..", "data", "raw", "new_articles.csv")
    empty_file = False
    try: 
        pd.read_csv(csv_path)
    except FileNotFoundError: 
        empty_file = True

    # Iterate over each post in the RSS feed
    for post in posts: 
        # Convert the published date to a datetime object removing the BST part
        date_without_bst = " ".join(post.published.split(" ")[:-1])
        new_comparison_time = datetime.strptime(date_without_bst, news_format)

        # Extract team names from title and summary
        teams = get_team_name(post.title + " " + post.summary)  

        # Check if the post's published date is within the specified range, has the tag "News Story" or "Article/Blog",
        # has teams, and is not already in the previous data
        if new_comparison_time >= lower_comparison_time \
            and new_comparison_time <= upper_comparison_time \
            and post.tags[0].term in ("News Story", "Article/Blog") \
            and teams:

            print(post.link)
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

    
    # Append the new data to the CSV file if it is not empty, otherwise create a new CSV file
    if not empty_file: 
        new_data.to_csv(csv_path, mode="a", index=False, header=False)
    else: 
        new_data.to_csv(csv_path, index=False)
    
