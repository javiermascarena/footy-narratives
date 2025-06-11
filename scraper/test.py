import requests
from bs4 import BeautifulSoup


url = "https://www.bbc.com/sport/football/articles/cr7zyn3e9ygo"
# Send a GET request to the URL
page = requests.get(url)
soup = BeautifulSoup(page.content, "html.parser")

# Find the author name in the HTML content
# If the author is not found, return an empty string
author = soup.find(class_="ssrcss-12jkbjf-Text-TextContributorName e19uhciu6")
if author:
    author = author.text.strip()
else: 
    author = ""

# Find the article body in the HTML content
# If the article body is not found, return an empty string
article = soup.find(class_="ssrcss-4vng7l-ArticleWrapper e1nh2i2l3")
html_text = article.find_all("p")
cleaned_text = ""
for paragraph in html_text: 
    cleaned_text += paragraph.text.strip() + "\n" 

print(f"Author: {author}")
print(f"Article: {cleaned_text}")
