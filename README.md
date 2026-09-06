# Books to Scrape: Polite, Idempotent Web Scraping Pipeline

A robust, fault-tolerant web scraping pipeline built in Python to extract structured catalog data from [Books to Scrape](https://books.toscrape.com). 

The scraper incorporates defensive engineering patterns: local disk caching for idempotency, respectful rate limiting, transient fault retries, Pydantic-based schema validation with a quarantine queue, and complete run observability.

---

## Key Features & Architecture

* **Idempotency via Cache-First Strategy:** Every requested catalogue and book detail page is cached locally as raw HTML. Re-running the pipeline reads from disk rather than dispatching redundant network calls, producing identical datasets without server strain.
* **Polite Crawling:** Implements custom `User-Agent` identification, 4.0-second timeouts, and mandatory `0.5s` delays between live HTTP requests.
* **Fault Tolerance & Transient Retries:**
  * **Transient Failures (5xx & Timeouts):** Pauses for 1.0s and retries once.
  * **Permanent Failures (4xx):** Aborts immediately without retrying to avoid server spam.
  * **Page-Level Isolation:** Individual book parsing errors are caught and logged without aborting the entire run.
* **Schema Validation & Dead-Letter Quarantine:** Every parsed book record is validated against a Pydantic `Record` schema:
  * Records passing validation are serialized to `output/books.json`.
  * Malformed records are quarantined in `output/errors.json` alongside detailed failure reasons.
* **Operational Observability:** Generates a structured JSON execution report (`output/run-report.json`) tracking timestamps, duration, cache hit rates, network request counts, and validation results.

---

## Directory Structure

```text
├── cache/                  # Local HTML cache directory (gitignored)
├── output/
│   ├── books.json          # Validated book records (JSON array)
│   ├── errors.json         # Quarantined invalid records with error traces
│   └── run-report.json     # Execution audit metrics and summary stats
├── scraper.py              # Main crawler and extraction pipeline
├── requirements.txt        # Pinned Python dependencies
├── .gitignore              # Ignores cache/, __pycache__/, .env, etc.
└── README.md
```

## Setup & Installation
**Prerequisites:**
* Python 3.10+
* pip package manager

```bash
git clone https://github.com/kamilnazarli/scraper.git
cd scraper

python -m venv venv
# On macOS / Linux:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (CMD):
.\.venv\Scripts\activate.bat
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Verification & Testing

### 1. Idempotency Test

- **First Run:** Downloads catalog pages and book details to `cache/`, making live network requests. Outputs metrics showing `pages_fetched > 0`.
- **Second Run:** Re-processes the data entirely from `cache/`. Finishes significantly faster with `cache_hits` matching the total number of pages and `pages_fetched = 0`.

This verifies that the pipeline correctly uses cached data and avoids unnecessary network requests on subsequent runs.

### 2. Synthetic Failure Verification

- Injecting a non-existent URL, such as:
  `https://books.toscrape.com/catalogue/fake_9999/index.html`
- The URL triggers the 404 handler.
- The pipeline logs the failure and increments `failed_pages` in `output/run-report.json`.
- Despite the failure, the pipeline continues safely and writes all **60 valid records** to `output/books.json`.

This verifies that a single failed page does not crash the entire pipeline or corrupt the successfully collected data.