import requests
from bs4 import BeautifulSoup

url = "https://www.skysports.com/football/news/11095/13383936/mathys-tel-transfer-tottenham-hotspur-complete-30m-deal-to-sign-bayern-munich-forward"

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

print(cleaned_text, author)