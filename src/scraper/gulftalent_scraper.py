#!/usr/bin/env python3
"""Collect all currently available Saudi job postings from GulfTalent."""

import argparse
import concurrent.futures
import csv
import html
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://www.gulftalent.com"
LIST_URL = BASE_URL + "/mobile/saudi-arabia/jobs"
USER_AGENT = "SDA-Data-Engineering-Student-Project/1.0"


def fetch(url: str, timeout: int = 25, retries: int = 3) -> str:
    last_error = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
            time.sleep(2 + attempt * 3)
    raise last_error


def listing_links(page_html: str) -> list[str]:
    paths = re.findall(
        r'href="(/mobile/saudi-arabia/jobs/(?!\d+/?")[^"?#]+-\d+)"',
        page_html,
        flags=re.IGNORECASE,
    )
    return list(dict.fromkeys(urljoin(BASE_URL, path) for path in paths))


def job_posting_json(page_html: str) -> dict:
    scripts = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in scripts:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    raise ValueError("No JobPosting structured data found")


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def clean_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    return " ".join(parser.parts)


def nested(data: dict, *keys: str) -> str:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key, "")
    return "" if current is None else str(current)


def normalize_company_url(company_name: str, raw_value: str) -> str:
    """Return a valid GulfTalent company URL when JSON-LD contains a name."""
    raw_value = (raw_value or "").strip()
    if re.match(r"^https?://", raw_value, flags=re.IGNORECASE):
        return raw_value

    decoded_name = html.unescape(company_name or "")
    ascii_name = unicodedata.normalize("NFKD", decoded_name).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return f"{BASE_URL}/companies/{slug}-careers" if slug else ""


def normalize_job(data: dict, url: str) -> dict:
    employment = data.get("employmentType", "")
    if isinstance(employment, list):
        employment = ",".join(map(str, employment))
    scrape_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    valid_through = data.get("validThrough", "")
    company_name = nested(data, "hiringOrganization", "name")
    raw_company_url = nested(data, "hiringOrganization", "sameAs") or nested(
        data, "hiringOrganization", "url"
    )
    company_url = normalize_company_url(company_name, raw_company_url)
    workplace_raw = str(data.get("jobLocationType", "")).upper()
    workplace_type = "Remote" if "TELECOMMUTE" in workplace_raw else ""
    salary = data.get("baseSalary")
    job_status = "active"
    if valid_through:
        try:
            expiry = datetime.fromisoformat(str(valid_through).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                job_status = "expired"
        except ValueError:
            pass
    return {
        "source_job_id": nested(data, "identifier", "value"),
        "job_title": data.get("title", ""),
        "url": url,
        "company_name": company_name,
        "company_url": company_url,
        "city": nested(data, "jobLocation", "address", "addressLocality"),
        "region": nested(data, "jobLocation", "address", "addressRegion"),
        "country": nested(data, "jobLocation", "address", "addressCountry"),
        "employment_type": employment,
        "workplace_type": workplace_type,
        "experience_years": nested(data, "experienceRequirements", "monthsOfExperience"),
        "job_category": data.get("occupationalCategory", ""),
        "industry": data.get("industry", ""),
        "is_salary_disclosed": bool(salary),
        "job_source": "GulfTalent",
        "job_posted_date": data.get("datePosted", ""),
        "job_status": job_status,
        "collected_at": scrape_time,
        "description": clean_html(data.get("description", "")),
    }


def collect(delay: float, start_page: int, max_pages: int, checkpoint: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    if checkpoint.exists():
        with checkpoint.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        # Backward compatibility with checkpoints created before the raw
        # source identifier was renamed.
        for row in rows:
            if "source_job_id" not in row:
                row["source_job_id"] = row.pop("job_id", "")
        print(f"Resuming from checkpoint with {len(rows)} rows", flush=True)
    seen_links: set[str] = {row.get("url", "") for row in rows}

    for page in range(start_page, max_pages + 1):
        page_url = LIST_URL if page == 1 else f"{LIST_URL}/{page}"
        try:
            page_links = listing_links(fetch(page_url))
        except Exception as exc:
            errors.append(f"Listing page {page}: {exc}")
            print(f"Listing page {page} failed; stopping.", flush=True)
            break
        links = [link for link in page_links if link not in seen_links]
        if not links:
            print(f"No new job links found on listing page {page}; stopping.", flush=True)
            break

        print(f"Listing page {page}: found {len(links)} new links", flush=True)
        seen_links.update(links)
        def collect_one(link: str):
            try:
                return normalize_job(job_posting_json(fetch(link)), link), ""
            except Exception as exc:
                return None, f"{link}: {exc}"

        # Small worker pool keeps collection practical while avoiding a large
        # burst of traffic to the source.
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            for row, error in executor.map(collect_one, links):
                if row:
                    rows.append(row)
                    print(f"Collected {len(rows)}: {row['job_title']}", flush=True)
                if error:
                    errors.append(error)
        write_csv(rows, checkpoint)
        print(f"Checkpoint saved after page {page}: {len(rows)} rows", flush=True)
        time.sleep(delay)
    return rows, errors


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_job_id", "job_title", "url", "company_name", "company_url", "city",
        "region", "country", "employment_type", "workplace_type",
        "experience_years", "job_category", "industry", "is_salary_disclosed",
        "job_source", "job_posted_date", "job_status", "collected_at",
        "description",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.75)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.delay < 0.5:
        parser.error("--delay must be at least 0.5 seconds")
    if not 1 <= args.max_pages <= 1000:
        parser.error("--max-pages must be between 1 and 1000")
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M")
    # Same convention as sabbar_scraper.py / tanqeeb_scraper.py: honor
    # OUTPUT_DIR so the file lands in the mounted volume that
    # upload_to_blob.py reads from, instead of the container's own
    # (ephemeral) working directory.
    output_dir = Path(os.environ.get("OUTPUT_DIR", "."))
    output_dir.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else output_dir / f"{stamp}_gulftalent_jobs.csv"
    rows, errors = collect(args.delay, args.start_page, args.max_pages, output)
    write_csv(rows, output)
    print(f"Saved {len(rows)} rows to {output}")
    if errors:
        print(f"Skipped {len(errors)} pages")


if __name__ == "__main__":
    main()