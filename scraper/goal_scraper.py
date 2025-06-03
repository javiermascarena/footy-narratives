import feedparser
from datetime import datetime
import pandas as pd
from aux_functions import get_team_name



if __name__ == "__main__":
    # URL of the Goal RSS feed to parse
    url = "https://rss.app/feeds/8HR6vLhbPFjKrvET.xml"

    # Parse the RSS feed and store the results
    newsfeed = feedparser.parse(url)
    posts = newsfeed.entries

    print(posts[0].published)

    # Define the lower and upper date boundaries as strings
    lower_time_bound = "2025-05-01"
    upper_time_bound = "2025-06-04"
    # Define the format for the boundaries and convert strings to datetime 
    common_format = "%Y-%m-%d"
    lower_comparison_time = datetime.strptime(lower_time_bound, common_format)
    upper_comparison_time = datetime.strptime(upper_time_bound, common_format)

    # Define the format for the published date in the RSS feed entries
    news_format = "%a, %d %b %Y %H:%M:%S"

    # Create an empty DataFrame to store the results
    data = pd.DataFrame(columns=["Title", "Summary", "Link", "Date", "Author", "Teams"])

    # Iterate over each post in the RSS feed
    for post in posts: 
        # Convert the published date to a datetime object removing the GMT part
        date_without_gmt = " ".join(post.published.split(" ")[:-1])
        new_comparison_time = datetime.strptime(date_without_gmt, news_format)

        # Extract team names from title and summary
        teams = get_team_name(post.title + " " + post.summary)  

        # Check if the post's published date is within the specified range and if it has the tag "News Story"
        if new_comparison_time >= lower_comparison_time and new_comparison_time <= upper_comparison_time and teams:
            # Append the post details to the DataFrame
            post = {
                "Title": post.title,
                "Summary": post.summary,
                "Link": post.link,
                "Date": new_comparison_time.strftime(news_format),
                "Author": post.author if 'author' in post else 'Unknown',
                "Teams": teams
            }
            data = pd.concat([data, pd.DataFrame([post])], ignore_index=True)

    # Display the DataFrame
    print(data)
