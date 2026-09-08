import requests as rs
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Request headers — mimicking a real browser so the site doesn't block us or detect a bot
HEADERS = {
    "accept": "application/x-clarity-gzip",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "ar,en-US;q=0.9,en;q=0.8",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "referer": "https://saudi.tanqeeb.com/",
}

# Reuse one TCP connection instead of opening a new one per request — faster + lighter
session = rs.Session()
session.headers.update(HEADERS)

# How many job-description pages to fetch at the same time.
# Lowered from 8 -> 4 since higher parallelism seems to be triggering the site's rate limiting (403s).
MAX_WORKERS = 4

# Retry settings: if we get a 403/429 (blocked/rate-limited) or a network error
# (connection dropped, DNS failure, timeout), wait and try again instead of giving up immediately.
MAX_RETRIES = 5
BASE_BACKOFF = 5  # seconds; grows with each retry (5, 10, 20, 40, 80...)

# ---------------------------------------------------------------------------
# Output path: works both when run locally and inside Docker.
# - Locally: falls back to <project_root>/data/raw_data automatically.
# - In Docker: set the OUTPUT_DIR env var (e.g. via `ENV OUTPUT_DIR=/App/data/raw_data`
#   in the Dockerfile, or `docker run -e OUTPUT_DIR=...`) to override it.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "raw_data")

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract(card, class_name):
    """
    Generic helper: finds an element inside a job card by its CSS class
    and returns its stripped text, or an empty string "" if the element
    doesn't exist (avoids repeating the same try/except logic for every field)
    """
    el = card.find(class_=class_name)
    return el.get_text(strip=True) if el else ""


def get_with_retry(url, max_retries=MAX_RETRIES):
    """
    GETs a URL, retrying with growing delays if we hit:
      - 403 (blocked) / 429 (rate-limited)
      - a network-level exception (dropped connection, DNS failure, timeout)
    Returns the final response, or None if every retry was exhausted
    without ever getting a response back.
    A small random jitter is added so parallel threads don't all retry at the exact same moment.
    """
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
        except (rs.exceptions.ConnectionError, rs.exceptions.Timeout) as e:
            wait = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 2)
            print(f"  Network error on {url}: {e} — retry {attempt + 1}/{max_retries}, waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in (403, 429):
            wait = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 2)
            print(f"  Got {response.status_code} on {url} — retry {attempt + 1}/{max_retries}, waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        # Any other status code:
        # - 404/410 = the job posting is gone/removed permanently -> retrying won't help, skip immediately
        # - other codes (500, etc.) -> also not worth retrying here, return as-is
        if response.status_code in (404, 410):
            print(f"  Job page gone (status {response.status_code}) on {url} — skipping, no retry")
        return response

    # Ran out of retries without ever getting a usable response (e.g. persistent network outage)
    print(f"  Giving up on {url} — exhausted all {max_retries} retries")
    return None


def fetch_description(job_url):
    """
    Fetches a single job's full description from its own page.
    Returns (job_url, description) so we can match it back up later.
    """
    if not job_url:
        return job_url, ""

    full_url = job_url if job_url.startswith("http") else "https://saudi.tanqeeb.com" + job_url
    try:
        job_response = get_with_retry(full_url)
        if job_response is None or job_response.status_code != 200:
            status = job_response.status_code if job_response is not None else "no response"
            if job_response is None or job_response.status_code not in (404, 410):
                print(f"Giving up on {full_url} after retries (status {status})")
            return job_url, ""
        job_soup = bs(job_response.content, "lxml")
        description_el = job_soup.find(id="jobDescriptionBody")
        return job_url, (description_el.get_text(strip=True) if description_el else "")
    except Exception as e:
        print(f"Failed to fetch description for {full_url}: {e}")
        return job_url, ""


# Search query parameters sent with each page URL (site filters: keywords, country, category...)
QUERY = "keywords=&country=54&state=0&category=-1&workplace=0&search_period=0&lang=all"

all_jobs = []       # list to store every job collected across all pages
seen_urls = set()   # set to track job URLs we've already collected, to avoid duplicates

try:
    # Loop through pages from 1 to 9999 (large upper bound as a safety cap; actual stopping happens below)
    for page in range(1, 10000):
        url = f"https://saudi.tanqeeb.com/jobs/search/page/{page}?{QUERY}"
        response = get_with_retry(url)

        # If the page still fails after retries (or the network is down entirely), stop the whole loop
        if response is None or response.status_code != 200:
            status = response.status_code if response is not None else "no response (network error)"
            print(f"Page {page}: failed with status {status} after retries — stopping")
            break

        # Parse the page's HTML into a BeautifulSoup object so we can search through it
        soup = bs(response.content, "lxml")

        # Grab all job cards on this page
        job_cards = soup.find_all(class_="search-job-card")
        print(f"Page {page}: found {len(job_cards)} jobs")

        # No job cards on this page means we've reached the last page → stop
        if len(job_cards) == 0:
            print("No more jobs. Stopping.")
            break

        # First pass: build the basic job records (no description yet) and collect
        # the list of new URLs whose descriptions we still need to fetch.
        page_jobs = {}       # job_url -> job dict (without description yet)
        urls_to_fetch = []   # new, not-yet-seen job URLs on this page

        for card in job_cards:
            title_el = card.find(class_="search-job-title-link")
            job_url = title_el.get("href") if title_el else ""

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            # The site reuses the same "search-job-tag" class for BOTH the job-type
            # tag (Full Time / Part Time) AND the experience tag (e.g. "2 to 6 years").
            # card.find(class_="search-job-tag") used to just grab whichever one came
            # first in the HTML, mixing the two together in the job_type column.
            # grab ALL tag elements, identify the experience one specifically,
            # and treat any other tag as the job type.
            tag_els = card.select(".search-job-tag")
            experience_el = card.select_one(".search-job-tag.search-job-tag-exp")
            job_type_el = next((el for el in tag_els if el is not experience_el), None)

            job = {
                "job_title": extract(card, "search-job-title-link"),
                "url": job_url,
                "company_name": extract(card, "search-job-company-name"),
                "location": extract(card, "search-job-workplace-location"),
                "job_posted_date": extract(card, "search-job-date"),
                "job_type": job_type_el.get_text(strip=True) if job_type_el else "",
                "experience_years": experience_el.get_text(strip=True) if experience_el else "",
                "job_source": extract(card, "search-job-source"),
                "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": "",
            }
            page_jobs[job_url] = job
            if job_url:
                urls_to_fetch.append(job_url)

        # Second pass: fetch all descriptions for this page's jobs IN PARALLEL
        # instead of one-by-one — this is the big time saver.
        if urls_to_fetch:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(fetch_description, u) for u in urls_to_fetch]
                for future in as_completed(futures):
                    job_url, description = future.result()
                    page_jobs[job_url]["description"] = description

        all_jobs.extend(page_jobs.values())

        # Small delay between PAGES with a bit of random jitter, so requests
        # don't look perfectly robotic (exactly N seconds apart every time).
        time.sleep(1 + random.uniform(0, 1))

except Exception as e:
    # Catch anything unexpected (not just network errors) so we still save
    # whatever was collected so far instead of losing it all.
    print(f"Unexpected error, stopping early: {e}")

finally:
    print(f"\nTotal unique jobs collected: {len(all_jobs)}")

    if all_jobs:
        # Output filename includes today's date, so each run produces a distinct file
        filename = os.path.join(OUTPUT_DIR, f"{datetime.date.today():%Y-%m-%d}_tanqeeb_jobs.csv")

        df = pd.DataFrame(all_jobs)
        df = df[[
            "job_title", "url", "company_name", "location", "job_posted_date",
            "job_type", "experience_years", "job_source", "collected_at", "description",
        ]]

        # If the URL is relative (starts with /), prepend the site's base URL
        df["url"] = df["url"].apply(
            lambda u: "https://saudi.tanqeeb.com" + u if isinstance(u, str) and u.startswith("/") else u
        )

        # utf-8-sig ensures Arabic text displays correctly when opened in Excel
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Saved {len(all_jobs)} jobs to {filename}")
    else:
        print("No jobs collected — nothing to save.")