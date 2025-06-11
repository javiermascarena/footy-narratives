import requests
from bs4 import BeautifulSoup


url = "https://www.skysports.com/football/news/11095/13378956/bryan-mbeumo-man-utd-register-initial-interest-with-brentford-to-sign-60m-rated-forward"
page = requests.get(url)
soup = BeautifulSoup(page.content, "html.parser")

author = soup.find(class_="sdc-article-author__name").text.strip()
article = soup.find(class_="sdc-article-body sdc-article-body--lead")
html_text = article.find_all("p", recursive=False)
cleaned_text = ""
for paragraph in html_text: 
    cleaned_text += paragraph.text.strip() + "\n"

print(f"THE AUTHOR IS: \n\n{author}\n\n")
print(f"THE ARTICLE IS: \n\n{cleaned_text}")