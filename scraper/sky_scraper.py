import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name
from newspaper import Article
import re
from typing import Tuple


def get_details_from_url(url) -> Tuple[str, str]:
    """
    Extracts the article text and authors from a given URL. 
    Args:
        url (str): The URL of the article to be processed.
    Returns:
        Tuple[str, str]: A tuple containing the cleaned article text and the author's name.
    """
    # Create an Article object and download the content
    article = Article(url)
    article.download()
    article.parse()
    # Extract authors and text from the article
    authors = article.authors if article.authors else ["Unknown"]
    text = article.text

    # Clean the text by removing cookie-related phrases and extra newlines
    chrome_phrase = "Please use Chrome browser for a more accessible video player "
    cookies_phrase = "Datawrapper Datawrapper , which may be using cookies and other technologies. To show you this content, we need your permission to use cookies. You can use the buttons below to amend your preferences to enable Datawrapper cookies or to allow those cookies just once. You can change your settings at any time via the This content is provided by, which may be using cookies and other technologies. To show you this content, we need your permission to use cookies. You can use the buttons below to amend your preferences to enablecookies or to allow those cookies just once. You can change your settings at any time via the Privacy Options Unfortunately we have been unable to verify if you have consented to Datawrapper cookies. To view this content you can use the button below to allow Datawrapper cookies for this session only. Enable Cookies Allow Cookies Once"
    text_withouth_cookies = text.replace(chrome_phrase, "").replace(cookies_phrase, "")
    cleaned_text = re.sub(r"\n+", " ", text_withouth_cookies)

    return (cleaned_text, authors[0])


if __name__ == "__main__":
    # URL of the SkySports RSS feed to parse
    url = "https://www.skysports.com/rss/11095"

    # Parse the RSS feed and store the results
    newsfeed = feedparser.parse(url)
    posts = newsfeed.entries

    # Define the lower and upper date boundaries as strings
    lower_time_bound = "2025-05-01"
    upper_time_bound = "2025-06-30"
    # Define the format for the boundaries and convert strings to datetime 
    common_format = "%Y-%m-%d"
    lower_comparison_time = datetime.strptime(lower_time_bound, common_format)
    upper_comparison_time = datetime.strptime(upper_time_bound, common_format)

    # Define the format for the published date in the RSS feed entries
    news_format = "%a, %d %b %Y %H:%M:%S"

    # Create an empty DataFrame to store the results
    data = pd.DataFrame(columns=["Title", "Summary", "Link", "Date", "Author", "Teams", "Article"])

    # Iterate over each post in the RSS feed
    for post in posts: 
        # Convert the published date to a datetime object removing the BST part
        date_without_bst = " ".join(post.published.split(" ")[:-1])
        new_comparison_time = datetime.strptime(date_without_bst, news_format)

        # Extract team names from title and summary
        teams = get_team_name(post.title + " " + post.summary)  

        # Check if the post's published date is within the specified range and if it has the tag "News Story"
        if new_comparison_time >= lower_comparison_time and new_comparison_time <= upper_comparison_time \
            and post.tags[0].term in ("News Story", "Article/Blog", "Liveblog") and teams:
            # Append the post details to the DataFrame
            post = {
                "Title": post.title,
                "Summary": post.summary,
                "Link": post.link,
                "Date": new_comparison_time.strftime(news_format),
                "Author": get_details_from_url(post.link)[1],
                "Teams": teams,
                "Article": get_details_from_url(post.link)[0]
            }
            data = pd.concat([data, pd.DataFrame([post])], ignore_index=True)

    # Display the DataFrame
    print(data.iloc[1, 6])
