import requests
import os
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
import time
from datetime import datetime
import re

def if_exists(path, current_url):
    """
    To check path existence locally and
    if not send request to get content
    """
    if not path.exists():
        r = requests.get(current_url,
                         headers=headers,
                         timeout=3)
        r.encoding = "utf-8"
        time.sleep(0.5)
        
        if r.status_code == requests.codes.ok:
            path.write_text(r.text, encoding="utf-8")
        else:
            r.raise_for_status()

def clean_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

headers = {
    "user-agent": "https://github.com/kamilnazarli/scraper"
}

absolute_book_urls = []
unique_book_urls = []
raw_records  = []
pages_visited = 0

page_url = "https://books.toscrape.com/catalogue/"
current_url = "https://books.toscrape.com/catalogue/page-1.html"

cache_dir = Path("cache")
cache_dir.mkdir(parents=True, exist_ok=True)
cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html"


while pages_visited < 3:
    each_page = {}  # to keep books on each page
    if_exists(cache_path, current_url)
            
    with open(cache_path,  encoding="utf-8") as fp:
        soup = BeautifulSoup(fp, 'html.parser')

        products = soup.find_all("article", class_="product_pod") # to get all books on current page

        for product in products:

            book_name = product.css.select("h3 > a")[0]["title"]  # title
            href = product.css.select("h3 > a")[0]["href"]
            # print(product.css.select("div > p"))
            
            book_url = urljoin(page_url, href)  # product url


            absolute_book_urls.append(book_url)
            each_page[f"{book_name}"] = book_url
            if book_url not in unique_book_urls:
                unique_book_urls.append(book_url)

        next_pages = soup.find("li", class_="next")
        next_href = next_pages.select("a")[0]["href"]


    for book_name, url in each_page.items():
        book_name = clean_filename(book_name)
        book_path = cache_dir / f"{book_name}.html"

        if_exists(book_path, url)  # check  existence locally
        fetched_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # fetched time

        with open(book_path, encoding="utf-8") as ps:
            page_soup = BeautifulSoup(ps, 'html.parser')
            pr = page_soup.find("div", class_="col-sm-6 product_main")

            title = book_name
            price = pr.css.select("p")[0].string  # price
            availability = pr.css.select("p")[1].contents[-1].strip() # availability text

            # print((pr.css.select("p")[2]["class"])) # returns a list
            rating = pr.css.select("p")[2]["class"][-1]  # rating

            desc_content = page_soup.find(id="product_description").find_next_sibling("p").string.strip()
            desc = (desc_content if desc_content else "") # description
            source_page = current_url # source page

            #  Keeping raw records of all books
            record = {
                "title": title,
                "product_url": url,
                "price_text": price,
                "availability_text": availability,
                "rating_text": rating,
                "description": desc,
                "source_page": source_page,
                "fetched_at": fetched_at
            }
            raw_records.append(record)
            

    pages_visited += 1 # to keep record of pages
    cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html"
    current_url = f"https://books.toscrape.com/catalogue/page-{pages_visited + 1}.html"


print(f"Catalogue pages: {pages_visited}")
print(f"Discovered: {len(absolute_book_urls)}")
print(f"Unique urls: {len(unique_book_urls)}")
