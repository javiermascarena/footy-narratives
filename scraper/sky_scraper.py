import feedparser
from datetime import datetime

# URL of the SkySports RSS feed to parse
url = "https://www.skysports.com/rss/11095"

# Parse the RSS feed and store the results
newsfeed = feedparser.parse(url)
posts = newsfeed.entries

# Define the lower and upper date boundaries as strings
lower_time_bound = "2025-05-01"
upper_time_bound = "2025-06-02"
# Define the format for the boundaries and convert strings to datetime 
common_format = "%Y-%m-%d"
lower_comparison_time = datetime.strptime(lower_time_bound, common_format)
upper_comparison_time = datetime.strptime(upper_time_bound, common_format)

# Define the format for the published date in the RSS feed entries
news_format = "%a, %d %b %Y %H:%M:%S"
n_posts = 0

# Iterate over each post in the RSS feed
for post in posts: 
    # Convert the published date to a datetime object removing the BST part
    date_without_bst = " ".join(post.published.split(" ")[:-1])
    new_comparison_time = datetime.strptime(date_without_bst, news_format)

    # Check if the post's published date is within the specified range and if it has the tag "News Story"
    if new_comparison_time >= lower_comparison_time and new_comparison_time <= upper_comparison_time \
        and post.tags[0].term == "News Story":
        # Print the post details
        print(f"\n--------- POST {n_posts+1} ---------")
        print("Post Title: ", post.title)
        print("Post Summary: ", post.summary)
        print("Post Link: ", post.link)
        print("Post Date: ", post.published)
        print("Post Tags: ", post.tags)

        n_posts += 1
