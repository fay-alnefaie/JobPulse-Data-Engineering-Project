import requests as rs
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
import time
import random
import os
import re

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

# Retry settings: if we get a 403/429 (blocked/rate-limited) or a network error
# (connection dropped, DNS failure, timeout), wait and try again instead of giving up immediately.
MAX_RETRIES = 7
BASE_BACKOFF = 5  # seconds; grows with each retry (5, 10, 20, 40, 80, 160, 320...)

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


def get_with_retry(url, max_retries=MAX_RETRIES):
    """
    GETs a URL, retrying with growing delays if we hit:
      - 403 (blocked) / 429 (rate-limited)
      - a network-level exception (dropped connection, DNS failure, timeout)
    Returns the final response, or None if every retry was exhausted
    without ever getting a response back.
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

        if response.status_code in (403, 429, 502, 503, 504):
            wait = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 2)
            print(f"  Got {response.status_code} on {url} — retry {attempt + 1}/{max_retries}, waiting {wait:.1f}s")
            time.sleep(wait)
            continue

        # Any other status code (404/410/500...) — not worth retrying, return as-is
        return response

    print(f"  Giving up on {url} — exhausted all {max_retries} retries")
    return None


def attr(card, name, default=None):
    """
    Shorthand for reading a data-job-* attribute off a job card. Returns `default`
    (None) both when the attribute is missing AND when it's present but empty
    (e.g. data-job-salary="") — the site uses "" for "not provided", but we want
    that to show up as a real empty/NULL cell in the CSV, not as a literal "" string.
    """
    value = card.get(name)
    if not isinstance(value, str):
        return default
    value = value.strip()
    return value if value else default


# Tanqeeb's "state" field is actually the CITY (e.g. "Jeddah", "Riyadh"), not the
# official Saudi administrative region. The site never exposes region at all, so we
# derive it ourselves from a lookup table built from Saudi Arabia's 13 administrative
# regions, matched against the exact city names/spellings this site uses in its own
# location filter (e.g. "Al Damam" for Dammam, "Nagran" for Najran).
CITY_TO_REGION = {
    "Riyadh": "Riyadh Region",
    "Jeddah": "Makkah Region",
    "Makkah": "Makkah Region",
    "Taif": "Makkah Region",
    "Al Taif": "Makkah Region",
    "Rabigh": "Makkah Region",
    "Medina": "Madinah Region",
    "Madinah": "Madinah Region",
    "Yanbu": "Madinah Region",
    "Eastern": "Eastern Province",
    "Eastern Province": "Eastern Province",
    "Al Damam": "Eastern Province",
    "Dammam": "Eastern Province",
    "Khobar": "Eastern Province",
    "Dhahran": "Eastern Province",
    "Jubail": "Eastern Province",
    "Qatif": "Eastern Province",
    "Al Ahsa": "Eastern Province",
    "Hafar Al-Batin": "Eastern Province",
    "Asir": "Asir Region",
    "Abha": "Asir Region",
    "Khamis Mushait": "Asir Region",
    "Bisha": "Asir Region",
    "Tabuk": "Tabuk Region",
    "Qassim": "Qassim Region",
    "Hail": "Hail Region",
    "Jouf": "Al Jouf Region",
    "Al Jouf": "Al Jouf Region",
    "Bahah": "Al Bahah Region",
    "Al Bahah": "Al Bahah Region",
    "Jizan": "Jazan Region",
    "Nagran": "Najran Region",
    "Najran": "Najran Region",
    "Northern Borders": "Northern Borders Region",
}

# Labels the site uses for workplace nature — filtered out when we fall back to
# parsing the "On-site - Saudi - Jeddah" style text (see parse_location below).
_WORKPLACE_LABELS = {"on-site", "remote", "hybrid"}


def parse_location(card):
    """
    Returns (country, city, region) for a job card.
    Prefers the direct data-job-country / data-job-state attributes (present on
    ~85% of cards). When either is missing, falls back to parsing the human-readable
    "On-site - Saudi - Jeddah" text in data-job-workplace-location, which is present
    on effectively every card. `region` is never in the source data — it's derived
    from CITY_TO_REGION and will be "" for any city not yet in that table.
    """
    country = attr(card, "data-job-country")
    city = attr(card, "data-job-state")

    if not country or not city:
        loc_text = attr(card, "data-job-workplace-location") or attr(card, "data-job-location") or ""
        parts = [p.strip() for p in loc_text.split("-") if p.strip()]
        parts = [p for p in parts if p.lower() not in _WORKPLACE_LABELS]
        if not country and parts:
            country = parts[0]
        if not city and len(parts) >= 2:
            city = parts[-1]

    region = CITY_TO_REGION.get(city)  # None if city is None or not in the table
    return country, city, region


# Some employers paste rich content (e.g. an entire Word/Excel table) into the job
# description, and the site double-escapes it — one level of HTML-entity escaping to
# store it safely inside the hidden div, PLUS a second level for the pasted content
# itself. A single get_text() only undoes the first level, leaving literal tag text
# like "<table><tr><td>..." in the result instead of clean text.
_TAG_LIKE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>")


def clean_description(desc_el):
    """
    Extracts the description text from its hidden div, re-parsing as HTML repeatedly
    (up to 3 passes) until no more literal HTML tags remain — this handles both
    normally-escaped and double-escaped descriptions the same way.
    """
    if desc_el is None:
        return None

    text = desc_el.get_text(separator=" ", strip=True)
    for _ in range(3):
        if not _TAG_LIKE.search(text):
            break
        text = bs(text, "lxml").get_text(separator=" ", strip=True)

    # Collapse repeated whitespace left over from stripped tags/table cells
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_job_card(card):
    """
    Extracts a full job record straight from a single <article data-drawer-trigger="job-card">
    element on the search-results page. Tanqeeb bakes essentially the entire job record —
    including experience, industry, location, and even the FULL description — into
    data-job-* attributes and a hidden div on this same page. That means we never need to
    open the job's own page just to read its description, which is what was making the old
    version of this script so slow (one extra HTTP request per job).

    Note: career_level, nationality, local_only, skills, district, and contact_name/email/phone
    are deliberately NOT extracted here — a full-run check showed they're 90-100% empty across
    the site (employers almost never fill them in), so keeping them just added noise to the CSV.
    is_confidential_company, education, gender, and keywords were dropped too, to keep the
    output aligned with the star_schema dims (dim_location, dim_employment_type, etc.).
    """
    job_url = attr(card, "data-job-url")

    # The full description is stored HTML-escaped inside a hidden div — sometimes
    # double-escaped when an employer pastes a rich table. clean_description()
    # handles both cases and returns plain text (or None if the div is missing/empty).
    desc_el = card.find(class_="job-card-description-source")
    description = clean_description(desc_el)

    country, city, region = parse_location(card)

    return {
        "source_job_id": attr(card, "data-job-id"),
        "job_title": attr(card, "data-job-name"),
        "url": job_url,
        "company_name": attr(card, "data-job-company"),
        "company_url": attr(card, "data-job-company-url"),
        "city": city,
        "region": region,
        "country": country,
        # employment_type (dim_employment_type): Full Time / Part Time / Contract / Internship...
        "employment_type": attr(card, "data-job-type"),
        # workplace_type: On-site / Remote / Hybrid — kept separate from employment_type on purpose
        "workplace_type": attr(card, "data-job-workplace"),
        "experience_years": attr(card, "data-job-experience"),
        "job_category": attr(card, "data-job-categories"),
        "industry": attr(card, "data-job-industry"),
        "is_salary_disclosed": attr(card, "data-job-salary") is not None,
        "job_source": attr(card, "data-job-source"),
        "job_posted_date": attr(card, "data-job-date"),
        "job_status": "closed" if attr(card, "data-job-closed") == "1" else "active",
        "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
    }


# Search query parameters sent with each page URL (site filters: keywords, country, category...)
# order_by=most_recent (instead of the site's default "relevance") is critical here:
# relevance ranking shifts every time a new job gets posted, which — combined with
# offset-based page numbers — causes "pagination drift": pages you already scraped
# reshuffle underneath you, so later pages return jobs you already saw instead of new
# ones. Sorting by date is stable regardless of how many jobs get posted mid-scrape.
QUERY = "keywords=&country=54&state=0&category=-1&workplace=0&search_period=0&lang=all&order_by=most_recent"

all_jobs = []       # list to store every job collected across all pages
seen_ids = set()    # set to track job IDs we've already collected, to avoid duplicates
consecutive_empty_pages = 0
MAX_CONSECUTIVE_EMPTY_PAGES = 3  # stop early if pagination is drifting (site reshuffled underneath us)

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

        soup = bs(response.content, "lxml")

        # Each job card is an <article data-drawer-trigger="job-card" data-job-id="..." ...>.
        # This single selector gets us the element that carries ALL the data-job-* attributes
        # AND the hidden description div — no per-job page visit required.
        job_cards = soup.select('article[data-drawer-trigger="job-card"]')
        print(f"Page {page}: found {len(job_cards)} jobs")

        if len(job_cards) == 0:
            print("No more jobs. Stopping.")
            break

        new_on_page = 0
        for card in job_cards:
            job_id = attr(card, "data-job-id")
            if job_id and job_id in seen_ids:
                continue
            if job_id:
                seen_ids.add(job_id)

            all_jobs.append(parse_job_card(card))
            new_on_page += 1

        print(f"  -> {new_on_page} new jobs added (total so far: {len(all_jobs)})")

        if new_on_page == 0:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= MAX_CONSECUTIVE_EMPTY_PAGES:
                print(
                    f"  {consecutive_empty_pages} consecutive pages with 0 new jobs — "
                    "pagination likely drifted (site reshuffled while scraping). Stopping."
                )
                break
        else:
            consecutive_empty_pages = 0

        # Small delay between PAGES with a bit of random jitter, so requests
        # don't look perfectly robotic (exactly N seconds apart every time).
        # No more per-job requests, so this is now the ONLY delay in the whole run.
        time.sleep(1 + random.uniform(0, 1))

except Exception as e:
    # Catch anything unexpected so we still save whatever was collected so far
    # instead of losing it all.
    print(f"Unexpected error, stopping early: {e}")

finally:
    print(f"\nTotal unique jobs collected: {len(all_jobs)}")

    if all_jobs:
        # Includes the time (not just the date) so re-running the script the same day
        # never collides with a previous file that might still be open (e.g. in Excel),
        # which is what caused the earlier PermissionError.
        filename = os.path.join(OUTPUT_DIR, f"{datetime.datetime.now():%Y-%m-%d_%H-%M}_tanqeeb_jobs.csv")

        df = pd.DataFrame(all_jobs)
        df = df[[
            "source_job_id", "job_title", "url", "company_name", "company_url",
            "city", "region", "country",
            "employment_type", "workplace_type",
            "experience_years", "job_category", "industry", "is_salary_disclosed",
            "job_source", "job_posted_date", "job_status", "collected_at", "description",
        ]]

        # If the URL is relative (starts with /), prepend the site's base URL
        df["url"] = df["url"].apply(
            lambda u: "https://saudi.tanqeeb.com" + u if isinstance(u, str) and u.startswith("/") else u
        )
        df["company_url"] = df["company_url"].apply(
            lambda u: "https://saudi.tanqeeb.com" + u if isinstance(u, str) and u.startswith("/") else u
        )

        # utf-8-sig ensures Arabic text displays correctly when opened in Excel
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Saved {len(all_jobs)} jobs to {filename}")
    else:
        print("No jobs collected — nothing to save.")