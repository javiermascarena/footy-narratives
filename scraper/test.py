import requests
from bs4 import BeautifulSoup


url = "https://www.bbc.com/sport/football/articles/cr7zyn3e9ygo"
# Send a GET request to the URL
page = requests.get(url)
soup = BeautifulSoup(page.content, "html.parser")

# Find the author name in the HTML content
# If the author is not found, return an empty string
author = soup.find("div", attrs={"data-component": "byline-block"}).find(class_="ssrcss-12jkbjf-Text-TextContributorName e19uhciu6")
if author:
    author = author.text.strip()
else: 
    author = ""

# Find the article body in the HTML content
# If the article body is not found, return an empty string
text_blocks = soup.find_all("div", attrs={"data-component": ["text-block","subheadline-block"]})

cleaned_text = ""
for block in text_blocks:
    html_text = block.find_all(["p", "h2"])
    for paragraph in html_text: 
        cleaned_text += paragraph.text.strip() + "\n" 


print(f"Author: {author}")
print(f"Article: {cleaned_text}")
