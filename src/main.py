import requests
import os
from pathlib import Path

headers = {
    "user-agent": "https://github.com/kamilnazarli/scraper"
}
    
path = Path(f"cache/catalogue-page-1.html")
path.parent.mkdir(parents=True, exist_ok=True)

if not path.exists():
    r = requests.get(f"https://books.toscrape.com/catalogue/page-1.html",
                     headers=headers,
                     timeout=3)

    if r.status_code == requests.codes.ok:
        path.write_text(r.text, encoding="utf-8")
    else:
        r.raise_for_status()
else:
    print("This path already exists")

