import requests
from requests.exceptions import HTTPError, Timeout
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit

import time
from datetime import datetime

import re
from pydantic import BaseModel, ValidationError, HttpUrl
import json

class Record(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str
    price_gbp: float


def fetch_or_cache(path, current_url):
    """
    Ensures a page exists in local cache, fetching it from the web if missing.

    Implements a cache-first strategy with fault tolerance:
    1. Cache Hit: If `path` already exists on disk, skips network calls.
    2. Network Fetch: If missing, sends a polite HTTP GET request (0.5s delay).
    3. Retries: On 5xx server errors or timeouts, waits 1s and retries once.
    4. Permanent Failures: 4xx errors (e.g. 404, 403) and failed retries are 
       caught safely without raising exceptions.
    """
    if not path.exists():
        time.sleep(0.5)
        try:
            r = requests.get(current_url,
                             headers=headers,
                             timeout=4)
            r.encoding = "utf-8"
            
            if r.status_code == requests.codes.ok:
                path.write_text(r.text, encoding="utf-8")
                return "fetch"

            else:
                r.raise_for_status()
        except HTTPError as err:
            if 500 <= err.response.status_code < 600:
                time.sleep(1)
                try:
                    r = requests.get(current_url,
                                     headers=headers,
                                     timeout=4)
                    r.encoding = "utf-8"

                    if r.status_code == requests.codes.ok:
                        path.write_text(r.text, encoding="utf-8")
                        return "fetch"

                    else:
                        r.raise_for_status()
                except:
                    return None
            else:
                return None

        except Timeout as time_err:
            time.sleep(1)
            try:
                r = requests.get(current_url,
                                 headers=headers,
                                 timeout=4)
                r.encoding = "utf-8"
                if r.status_code == requests.codes.ok:
                    path.write_text(r.text, encoding="utf-8")
                    return "fetch"
                else:
                    r.raise_for_status()
            except:
                return None

    else:
        return "cache"


def clean_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

headers = {
    "user-agent": "https://github.com/kamilnazarli/scraper"
}

absolute_book_urls = []
unique_book_urls = []

pages_visited = 0
pages_fetched = 0
cache_hits = 0
failed_pages = 0

valid_records, invalid_records = [], []

page_url = "https://books.toscrape.com/catalogue/"
current_url = "https://books.toscrape.com/catalogue/page-1.html"

Path("output").mkdir(parents=True, exist_ok=True) # Output directory for keeping results
cache_dir = Path("cache") # Cache directory to keep files locally
cache_dir.mkdir(parents=True, exist_ok=True)

cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html" # general cache path

all_pages = {}  # to keep all book page urls

while pages_visited < 3:
    result = fetch_or_cache(cache_path, current_url)

    if result  == "fetch":
        pages_fetched += 1
        print("Fetching content from given url...")
    elif result == "cache":
        cache_hits += 1
        print("Getting content from cache...")
    else:
        failed_pages += 1
        print("Unable to fetch.")

    with open(cache_path,  encoding="utf-8") as fp:
        soup = BeautifulSoup(fp, 'html.parser')

        products = soup.find_all("article", class_="product_pod") # to get all books on current page

        for product in products:

            book_name = product.css.select("h3 > a")[0]["title"]  # title
            href = product.css.select("h3 > a")[0]["href"]
            book_url = urljoin(page_url, href)  # product url

            absolute_book_urls.append(book_url)
            all_pages[f"{book_name}"] = book_url
            if book_url not in unique_book_urls:
                unique_book_urls.append(book_url)

        next_pages = soup.find("li", class_="next")
        next_href = next_pages.select("a")[0]["href"]

    pages_visited += 1 # to keep record of current page
    cache_path = cache_dir / f"catalogue-page-{pages_visited + 1}.html"
    current_url = f"https://books.toscrape.com/catalogue/page-{pages_visited + 1}.html"

start_time = time.time() # start time to measure duration

# Adding non-existing url to our list to check its reliability
all_pages["book_name"] = "https://books.toscrape.com/catalogue/fake-nonexistent-book-9999/index.html"

for book_name, url in all_pages.items():
    book_name = clean_filename(book_name)
    book_path = cache_dir / f"{book_name}.html"

    result = fetch_or_cache(book_path, url)
    if result == "fetch":  # if fetched
        pages_fetched += 1
    elif result == "cache": # if cached
        cache_hits += 1
    else: # if failed
        failed_pages += 1
        print(f"Skipping failed page: {url}")
        continue

    fetched_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # fetched time

    with open(book_path, encoding="utf-8") as ps:
        page_soup = BeautifulSoup(ps, 'html.parser')
        pr = page_soup.find("div", class_="col-sm-6 product_main")

        title = book_name
        price = pr.css.select("p")[0].string  # price
        price_clean = re.sub(r"[^\d.]", "", price)
        price_gbp = float(price_clean) # raw price value
        availability = pr.css.select("p")[1].contents[-1].strip() # availability text

        # print((pr.css.select("p")[2]["class"])) # returns a list
        rating = pr.css.select("p")[2]["class"][-1]  # rating

        desc_tag = page_soup.find(id="product_description")   #.string.strip()
        desc = (desc_tag.find_next_sibling("p").string.strip() if desc_tag else None) # description
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
            "fetched_at": fetched_at,
            "price_gbp": price_gbp
        }

        # Validating each record before storing
        try:
            validated_record = Record(**record)
            valid_records.append(validated_record.model_dump(mode="json"))
        except ValidationError as e:
            invalid_records.append({
                "record": record,
                "reason": e.errors()})
duration_seconds = round(time.time() - start_time, 2)

# Report for the runtime
report = {
    "start_time": str(datetime.fromtimestamp(start_time)),
    "duration_seconds": duration_seconds,
    "pages_fetched": pages_fetched,
    "cache_hits": cache_hits,
    "valid_records": len(valid_records),
    "invalid_records": len(invalid_records),
    "failed_pages": failed_pages
}

# Write the result to JSON file
with open("output/books.json", "w", encoding="utf-8") as file:
    json.dump(valid_records, file, indent=4)

with open("output/errors.json", "w", encoding="utf-8") as file:
    json.dump(invalid_records, file, indent=4)

with open("output/run-report.json", "w", encoding="utf-8") as file:
    json.dump(report, file, indent=4)

print(f"Catalogue pages: {pages_visited}")
print(f"Discovered: {len(absolute_book_urls)}")
print(f"Unique urls: {len(unique_book_urls)}")
