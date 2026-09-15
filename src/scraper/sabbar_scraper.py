import requests as rs
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime
import time
import random
import os
import re
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Sabbar (sabbar.com) job scraper — CONCURRENT version.
#
# CHANGES IN THIS VERSION (fixes requested):
#   1) Switched every "/ar/jobs/..." URL to "/en/jobs/..." — this is the key
#      fix for city/country coming back in Arabic. Sabbar returns
#      cityValue/countryValue already localized to whatever language path
#      you request (/ar/ vs /en/), so using /en/ everywhere means we get
#      "Riyadh" / "Saudi Arabia" directly with no translation table needed.
#   2) industry and experience_years were coming back empty because the
#      code only checked ONE possible key name in the "big" JSON blob.
#      Sabbar's frontend payload isn't guaranteed to always use the same
#      key across job types, so we now try several plausible key names,
#      then fall back to the JSON-LD JobPosting block if still empty.
#   3) Output path no longer has any Claude-sandbox-specific logic — it's
#      just "<script folder>/output" by default, overridable with the
#      OUTPUT_DIR environment variable.
# ---------------------------------------------------------------------------

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,ar;q=0.5",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "referer": "https://sabbar.com/en/jobs",
}

MAX_RETRIES = 7
BASE_BACKOFF = 5  # seconds; grows with each retry (5, 10, 20, 40, 80, 160, 320...)

# Script lives at <project_root>/src/scraper/sabbar_scraper.py, so going up
# two levels from the script's folder lands on <project_root>, and the
# default output goes to <project_root>/data/raw_data.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw_data")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

_thread_local = threading.local()


def get_session():
    if not hasattr(_thread_local, "session"):
        s = rs.Session()
        s.headers.update(HEADERS)
        _thread_local.session = s
    return _thread_local.session


def get_with_retry(url, max_retries=MAX_RETRIES):
    session = get_session()
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=20)
        except rs.exceptions.RequestException as e:
            # Catches ConnectionError, Timeout, ChunkedEncodingError
            # (server cut the response mid-stream), and any other
            # network-level failure requests can raise — instead of only
            # the two specific ones we checked before, which let
            # ChunkedEncodingError crash the whole script.
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

        return response

    print(f"  Giving up on {url} — exhausted all {max_retries} retries")
    return None


# Region lookup stays keyed by internal city CODE (e.g. "SA_RIYADH"), which
# does not change between /ar/ and /en/ pages, so this table is unaffected
# by the ar->en switch.
CITY_CODE_TO_REGION = {
    "SA_RIYADH": "Riyadh Region",
    "SA_JEDDAH": "Makkah Region",
    "SA_MAKKAH": "Makkah Region",
    "SA_TAIF": "Makkah Region",
    "SA_MEDINA": "Madinah Region",
    "SA_MADINAH": "Madinah Region",
    "SA_YANBU": "Madinah Region",
    "SA_DAMMAM": "Eastern Province",
    "SA_KHOBAR": "Eastern Province",
    "SA_DHAHRAN": "Eastern Province",
    "SA_JUBAIL": "Eastern Province",
    "SA_QATIF": "Eastern Province",
    "SA_AL_AHSA": "Eastern Province",
    "SA_HOFUF": "Eastern Province",
    "SA_HAFAR_AL_BATIN": "Eastern Province",
    "SA_ABHA": "Asir Region",
    "SA_KHAMIS_MUSHAYT": "Asir Region",
    "SA_BISHA": "Asir Region",
    "SA_TABUK": "Tabuk Region",
    "SA_QASSIM": "Qassim Region",
    "SA_BURAYDAH": "Qassim Region",
    "SA_UNAYZAH": "Qassim Region",
    "SA_HAIL": "Hail Region",
    "SA_JOUF": "Al Jouf Region",
    "SA_SAKAKA": "Al Jouf Region",
    "SA_BAHAH": "Al Bahah Region",
    "SA_JIZAN": "Jazan Region",
    "SA_NAJRAN": "Najran Region",
    "SA_ARAR": "Northern Borders Region",
}

CONTRACT_TYPE_MAP = {
    "FULLTIME": "Full Time",
    "PARTTIME": "Part Time",
    "SEASONAL": "Seasonal",
    "INTERNSHIP": "Internship",
}
WORKPLACE_TYPE_MAP = {
    "ON_SITE": "On-site",
    "REMOTE": "Remote",
    "FIELD": "Field",
}
JOB_STATUS_MAP = {
    "OPEN": "active",
    "CLOSED": "closed",
}

# Switched from /ar/jobs/ to /en/jobs/ — this is what makes city/country
# come back in English straight from Sabbar, no translation needed.
JOB_LINK_RE = re.compile(r'^/en/jobs/[^"?#]+/id-[0-9a-fA-F-]{36}$')
JOB_ID_RE = re.compile(r'/id-([0-9a-fA-F-]{36})')


def _extract_push_strings(html):
    results = []
    marker = 'self.__next_f.push([1,"'
    idx = 0
    n = len(html)
    while True:
        start = html.find(marker, idx)
        if start == -1:
            break
        i = start + len(marker)
        while i < n:
            c = html[i]
            if c == "\\":
                i += 2
                continue
            if c == '"':
                break
            i += 1
        results.append(html[start + len(marker):i])
        idx = i + 1
    return results


def _unescape_js_string(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def build_flight_buffer(html):
    return "".join(_unescape_js_string(p) for p in _extract_push_strings(html))


def extract_json_object(buffer, marker_substring):
    idx = buffer.find(marker_substring)
    if idx == -1:
        return None
    brace_start = buffer.rfind("{", 0, idx)
    if brace_start == -1:
        return None
    i = brace_start
    depth = 0
    in_string = False
    n = len(buffer)
    while i < n:
        c = buffer[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return buffer[brace_start:i + 1]
        i += 1
    return None


def get_big_job_json(buffer, job_uuid):
    for marker in (f'"id":"{job_uuid}","partnerId"', f'"id":"{job_uuid}","partnerName"'):
        obj_str = extract_json_object(buffer, marker)
        if obj_str:
            try:
                return json.loads(obj_str)
            except Exception:
                continue
    return None


def extract_jsonld_jobposting(html):
    for m in re.finditer(
        r'<script type="application/ld\+json">(\{.*?"@type":"JobPosting".*?\})</script>',
        html, re.DOTALL,
    ):
        try:
            return json.loads(m.group(1))
        except Exception:
            continue
    return None


def clean_job_title_from_h1(soup):
    h1 = soup.find("h1")
    if not h1:
        return None
    title = h1.get_text(" ", strip=True)
    return title or None


def first_present(*values):
    """Return the first value that isn't None/''  (0 and False are kept,
    since they can be legit answers, e.g. 0 years of experience)."""
    for v in values:
        if v is not None and v != "":
            return v
    return None


def first_key(d, keys):
    """Return the first truthy value found among `keys` in dict `d`.
    Used to remove the repeated 'try key A, else key B, else key C' blocks
    that industry/experience_years/job_category all needed, since Sabbar's
    payload doesn't guarantee one fixed key name per field."""
    if not d:
        return None
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


def _format_num(raw):
    """'5' -> '5', '5.0' -> '5', '5.5' -> '5.5' — used when rebuilding a
    range string so we don't end up with '5.0-10.0'."""
    n = float(raw)
    return str(int(n)) if n.is_integer() else str(n)


def normalize_experience_years(value):
    if value is None:
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    value = str(value).strip()
    if not value:
        return None

    # Reject date-like values: 02/05/2026, 02-05-2026, etc.
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", value):
        return None

    # Accept simple values such as "2" or "2 years"
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)?", value, re.IGNORECASE)
    if match:
        number = float(match.group(1))
        return int(number) if number.is_integer() else number

    # "+10" / "10+" style values (seen in Sabbar's own enum labels, e.g.
    # "experienceYears_+10": "+10 Years") mean "10 years or more".
    plus_match = re.fullmatch(r"\+?\s*(\d+(?:\.\d+)?)\s*\+?", value)
    if plus_match and ("+" in value):
        return f"{_format_num(plus_match.group(1))}+ yrs"

    # Ranges like "5-10" or "5 - 10 years" — keep the full range as text
    # (e.g. "5-10 yrs"). The " yrs" suffix is deliberate: a bare "5-10" gets
    # auto-converted to a date (e.g. "02/05/2026") the moment the CSV is
    # opened in Excel, since Excel treats "N-N" cells as dates by default.
    range_match = re.match(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", value)
    if range_match:
        lo, hi = range_match.group(1), range_match.group(2)
        return f"{_format_num(lo)}-{_format_num(hi)} yrs"

    # Do not guess for other unexpected text.
    return None


# Key-name candidates to try, in order, for fields Sabbar doesn't expose
# under one guaranteed fixed name. Kept as module-level constants so the
# extraction functions below stay one-liners.
EXPERIENCE_KEYS = (
    "experienceYears", "experienceYearsValue", "minExperienceYears",
    "yearsOfExperience", "yearsOfExperienceValue", "experience",
    "experienceValue", "requiredExperienceYears",
)
INDUSTRY_KEYS = (
    "industryValue", "industry", "sectorValue", "sector",
    "categoryValue", "jobCategoryValue", "jobCategory",
)


def get_experience_years_raw(big, jsonld):
    """Years of experience: try known keys in `big`, else fall back to
    JSON-LD's experienceRequirements.monthsOfExperience (converted to years)."""
    val = first_key(big, EXPERIENCE_KEYS)
    if val is not None:
        return val

    exp_req = jsonld.get("experienceRequirements") if jsonld else None
    if isinstance(exp_req, dict):
        months = exp_req.get("monthsOfExperience")
        if months is not None:
            try:
                return float(months) / 12
            except (TypeError, ValueError):
                return None
    elif isinstance(exp_req, (str, int, float)):
        return exp_req

    return None


def get_industry_raw(big, jsonld):
    """Industry: try known keys in `big`, else fall back to JSON-LD's
    'industry' / 'occupationalCategory'."""
    return first_key(big, INDUSTRY_KEYS) or first_key(jsonld, ("industry", "occupationalCategory"))


def get_explicit_job_source(big, jsonld):
    if not big:
        return None

    for key in ("sourceName", "sourceValue", "jobSourceName", "jobSource"):
        value = big.get(key)
        if value:
            return str(value).strip()

    source = big.get("source")
    if source == "IN_PLATFORM":
        return "Sabbar"
    if source == "AGGREGATED":
        return "Aggregated (source not specified)"

    if source:
        return str(source).strip()

    return None


def parse_job_detail(url, delay_range=(0.6, 1.4)):
    time.sleep(random.uniform(*delay_range))

    resp = get_with_retry(url)
    if resp is None or resp.status_code != 200:
        return None

    html = resp.text
    soup = bs(html, "lxml")

    m = JOB_ID_RE.search(url)
    job_uuid = m.group(1) if m else None

    jsonld = extract_jsonld_jobposting(html) or {}

    big = None
    if job_uuid:
        try:
            buffer = build_flight_buffer(html)
            big = get_big_job_json(buffer, job_uuid)
        except Exception:
            big = None

    job_title = first_present(
        clean_job_title_from_h1(soup),
        big.get("jobPositionValue") if big else None,
    )

    # /en/ path here too, matching JOB_LINK_RE above
    company_link = soup.select_one('a[href*="/en/jobs/companies/"]')
    company_href = company_link.get("href") if company_link else None

    company_name = first_present(
        company_link.get_text(strip=True) if company_link else None,
        big.get("partnerName") if big else None,
        (jsonld.get("hiringOrganization") or {}).get("name"),
    )
    company_url = first_present(
        "https://sabbar.com" + company_href if company_href and company_href.startswith("/") else None,
        f"https://sabbar.com/en/jobs/companies/{big['partnerSlug']}" if big and big.get("partnerSlug") else None,
    )

    city_code = big.get("city") if big else None
    city = (big.get("cityValue") if big else None) or None
    region = CITY_CODE_TO_REGION.get(city_code) if city_code else None
    country = (big.get("countryValue") if big else None) or "Saudi Arabia"

    contract_code = big.get("contractType") if big else None
    employment_type = CONTRACT_TYPE_MAP.get(contract_code, contract_code)

    workplace_code = big.get("workplaceType") if big else None
    workplace_type = WORKPLACE_TYPE_MAP.get(workplace_code, workplace_code)

    experience_years = normalize_experience_years(get_experience_years_raw(big, jsonld))
    industry = get_industry_raw(big, jsonld)
    job_category = first_key(big, ("jobCategoryValue", "categoryValue"))

    salary_val = big.get("salary") if big else None
    if salary_val is None:
        base_salary = jsonld.get("baseSalary") or {}
        value = base_salary.get("value") or {}
        if isinstance(value, dict):
            salary_val = value.get("value")
    is_salary_disclosed = salary_val is not None

    job_source = get_explicit_job_source(big, jsonld)

    job_posted_date = None
    created_date = big.get("createdDate") if big else None
    if created_date:
        try:
            job_posted_date = datetime.datetime.utcfromtimestamp(created_date).strftime("%Y-%m-%d")
        except Exception:
            job_posted_date = None
    if not job_posted_date:
        job_posted_date = jsonld.get("datePosted")

    job_status_code = big.get("jobStatus") if big else None
    job_status = JOB_STATUS_MAP.get(job_status_code, "active")

    description = jsonld.get("description")
    if description:
        description = re.sub(r"<[^>]+>", " ", str(description))
        description = re.sub(r"[*_]+", "", description)
        description = re.sub(
            r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+",
            "",
            description,
        )
        description = re.sub(r"\s+", " ", description).strip()

    return {
        "source_job_id": job_uuid,
        "job_title": job_title,
        "url": url,
        "company_name": company_name,
        "company_url": company_url,
        "city": city,
        "region": region,
        "country": country,
        "employment_type": employment_type,
        "workplace_type": workplace_type,
        "experience_years": experience_years,
        "job_category": job_category,
        "industry": industry,
        "is_salary_disclosed": is_salary_disclosed,
        "job_source": job_source,
        "job_posted_date": job_posted_date,
        "job_status": job_status,
        "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
    }


def collect_job_urls(max_pages=None, start_page=1):
    urls = []
    seen = set()
    page = start_page
    consecutive_empty = 0
    MAX_CONSECUTIVE_EMPTY = 3

    while True:
        if max_pages and page > start_page + max_pages - 1:
            break

        # /en/ path here too
        list_url = f"https://sabbar.com/en/jobs?page={page}"
        resp = get_with_retry(list_url)
        if resp is None or resp.status_code != 200:
            status = resp.status_code if resp is not None else "no response (network error)"
            print(f"Listing page {page}: failed with status {status} — stopping")
            break

        soup = bs(resp.content, "lxml")
        page_urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if JOB_LINK_RE.match(href):
                full = "https://sabbar.com" + href
                if full not in seen:
                    seen.add(full)
                    page_urls.append(full)

        print(f"Listing page {page}: found {len(page_urls)} new job links (total so far: {len(seen)})")

        if not page_urls:
            consecutive_empty += 1
            if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                print(f"  {consecutive_empty} consecutive empty pages — assuming end of listing, stopping.")
                break
        else:
            consecutive_empty = 0

        urls.extend(page_urls)
        page += 1
        time.sleep(1 + random.uniform(0, 1))

    return urls


COLUMNS = [
    "source_job_id", "job_title", "url", "company_name", "company_url",
    "city", "region", "country",
    "employment_type", "workplace_type",
    "experience_years", "job_category", "industry", "is_salary_disclosed",
    "job_source", "job_posted_date", "job_status", "collected_at", "description",
]

csv_lock = threading.Lock()


def save_csv(jobs, filename):
    """Single place that writes the CSV — used for both the periodic
    checkpoint saves and the final save, so the two never drift apart."""
    pd.DataFrame(jobs)[COLUMNS].to_csv(filename, index=False, encoding="utf-8-sig")


def scrape_details_concurrently(job_urls, max_workers=10, checkpoint_every=25,
                                 detail_delay=(0.6, 1.4), output_filename=None):
    all_jobs = []
    completed = 0
    total = len(job_urls)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(parse_job_detail, url, detail_delay): url
            for url in job_urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                row = future.result()
            except Exception as e:
                print(f"  Error parsing {url}: {e}")
                row = None

            with csv_lock:
                completed += 1
                if row:
                    all_jobs.append(row)

                if completed % 10 == 0 or completed == total:
                    print(f"  [{completed}/{total}] processed — {len(all_jobs)} collected so far")

                if output_filename and completed % checkpoint_every == 0 and all_jobs:
                    save_csv(all_jobs, output_filename)

    return all_jobs


if __name__ == "__main__":
    MAX_LISTING_PAGES = None
    MAX_JOBS = None
    MAX_WORKERS = 10
    CHECKPOINT_EVERY = 25
    DETAIL_DELAY = (0.6, 1.4)

    job_urls = collect_job_urls(max_pages=MAX_LISTING_PAGES)
    print(f"\nTotal unique job URLs collected: {len(job_urls)}")

    if MAX_JOBS:
        job_urls = job_urls[:MAX_JOBS]

    filename = os.path.join(OUTPUT_DIR, f"{datetime.datetime.now():%Y-%m-%d_%H-%M}_sabbar_jobs.csv")

    all_jobs = scrape_details_concurrently(
        job_urls,
        max_workers=MAX_WORKERS,
        checkpoint_every=CHECKPOINT_EVERY,
        detail_delay=DETAIL_DELAY,
        output_filename=filename,
    )

    if all_jobs:
        save_csv(all_jobs, filename)
        print(f"\nSaved {len(all_jobs)} jobs to {filename}")
    else:
        print("\nNo jobs collected — nothing to save.") 
        # sumayah 