import requests
from bs4 import BeautifulSoup

class InternetRetriever:

    def fetch(self, url):
        try:
            html = requests.get(url, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)
            return text[:10000]  # limit
        except:
            return ""

internet_retriever = InternetRetriever()
