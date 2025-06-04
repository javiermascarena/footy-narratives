from newspaper import Article
import re

url = "https://www.skysports.com/football/news/11095/13378956/bryan-mbeumo-man-utd-register-initial-interest-with-brentford-to-sign-60m-rated-forward"
article = Article(url)
article.download()
article.parse()
authors = article.authors
text = article.text

chrome_phrase = "Please use Chrome browser for a more accessible video player "
cookies_phrase = "Datawrapper Datawrapper , which may be using cookies and other technologies. To show you this content, we need your permission to use cookies. You can use the buttons below to amend your preferences to enable Datawrapper cookies or to allow those cookies just once. You can change your settings at any time via the This content is provided by, which may be using cookies and other technologies. To show you this content, we need your permission to use cookies. You can use the buttons below to amend your preferences to enablecookies or to allow those cookies just once. You can change your settings at any time via the Privacy Options Unfortunately we have been unable to verify if you have consented to Datawrapper cookies. To view this content you can use the button below to allow Datawrapper cookies for this session only. Enable Cookies Allow Cookies Once"
text_withouth_cookies = text.replace(chrome_phrase, "").replace(cookies_phrase, "")
cleaned_text = re.sub(r"\n+", " ", text_withouth_cookies)

print(authors)
print(cleaned_text)