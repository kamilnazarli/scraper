import requests
import os
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
import time


headers = {
    "user-agent": "https://github.com/kamilnazarli/scraper"
}

absolute_book_urls = []
unique_book_urls = []
pages_visited = 0

page_url = "https://books.toscrape.com/catalogue/"
current_url = "https://books.toscrape.com/catalogue/page-1.html"

cache_dir = Path("cache")
cache_dir.mkdir(parents=True, exist_ok=True)
cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html"


while pages_visited < 3:
    if not cache_path.exists():
        r = requests.get(current_url,
                         headers=headers,
                         timeout=3)
        time.sleep(0.5)
    
        if r.status_code == requests.codes.ok:
            cache_path.write_text(r.text, encoding="utf-8")
        else:
            r.raise_for_status()
            
    with open(cache_path) as fp:
        soup = BeautifulSoup(fp, 'html.parser')

        products = soup.find_all("article", class_="product_pod")

        for product in products:
            book_name = product.css.select("h3 > a")[0]["title"]
            href = product.css.select("h3 > a")[0]["href"]
            book_url = urljoin(page_url, href)
            absolute_book_urls.append(book_url)
            if book_url not in unique_book_urls:
                unique_book_urls.append(book_url)

        next_pages = soup.find("li", class_="next")
        next_href = next_pages.select("a")[0]["href"]

    pages_visited += 1
    cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html"
    current_url = rf"https://books.toscrape.com/catalogue/page-{pages_visited + 1}.html"


print(f"Catalogue pages: {pages_visited}")
print(f"Discovered: {len(absolute_book_urls)}")
print(f"Unique urls: {len(unique_book_urls)}")

