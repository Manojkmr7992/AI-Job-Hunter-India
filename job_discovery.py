"""Step 4: safe, explicit job ingestion; no portal scraping or authentication."""
from __future__ import annotations
import csv
import io
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from core import add_job, evaluate

FIELDS = ('url', 'title', 'company', 'location', 'country', 'work_mode')
MAX_BYTES = 3_000_000


def parse_csv(data: bytes) -> list[dict]:
    if len(data) > MAX_BYTES:
        raise ValueError('CSV exceeds 3 MB limit')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Upload a UTF-8 CSV') from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
        raise ValueError('CSV must contain: ' + ', '.join(FIELDS))
    rows = []
    for i, row in enumerate(reader, 2):
        if i > 1001:
            raise ValueError('Maximum 1000 job rows per import')
        if None in row:
            raise ValueError(f'Line {i}: too many columns')
        rows.append({field: (row.get(field) or '').strip() for field in FIELDS})
    return rows


def normalize_job(job: dict) -> dict:
    cleaned = {field: str(job.get(field) or '').strip() for field in FIELDS}
    if cleaned['work_mode'].casefold() in ('on-site', 'on site'):
        cleaned['work_mode'] = 'Onsite'
    elif cleaned['work_mode'].casefold() in ('work from home', 'wfh'):
        cleaned['work_mode'] = 'Remote'
    if cleaned['country'].casefold() in ('in', 'india'):
        cleaned['country'] = 'India'
    if cleaned['location'].casefold() in ('bangalore', 'bengaluru'):
        cleaned['location'] = 'Bengaluru'
    if cleaned['location'].casefold() in ('hyderabad', 'pune'):
        cleaned['location'] = cleaned['location'].title()
    return cleaned


def import_jobs(jobs: list[dict], rules: dict, path=None, qualified_only=True) -> dict:
    """Persist eligible jobs using existing core.add_job. Returns per-row diagnostics."""
    saved, excluded, errors, seen = 0, 0, [], set()
    for i, raw in enumerate(jobs, 1):
        job = normalize_job(raw)
        url = job['url']
        if url in seen:
            continue
        seen.add(url)
        try:
            if qualified_only:
                ok, reason = evaluate(job, rules)
                if not ok:
                    excluded += 1
                    continue
            if path is None:
                add_job(job)
            else:
                add_job(job, path=path)
            saved += 1
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'Row {i}: {exc}')
    return {'saved_or_updated': saved, 'excluded': excluded, 'errors': errors,
            'duplicates_in_file': len(jobs) - len(seen)}


def greenhouse_jobs(board_token: str, timeout: int = 12) -> list[dict]:
    """Fetch public Greenhouse Job Board API data for a user-specified company board.

    Requires an explicit board token; does not crawl sites or bypass controls.
    Location and work mode are not reliably structured; returned records require review.
    """
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,80}', board_token):
        raise ValueError('Invalid Greenhouse board token')
    url = f'https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true'
    req = Request(url, headers={'User-Agent': 'AIJobHunterIndia/0.4 (public job board API)'})
    with urlopen(req, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Response exceeds 3 MB')
    payload = json.loads(raw.decode('utf-8'))
    result = []
    for item in payload.get('jobs', [])[:1000]:
        title = item.get('title') or ''
        location = (item.get('location') or {}).get('name') or ''
        link = item.get('absolute_url') or ''
        parsed = urlsplit(link)
        if not title or parsed.scheme != 'https' or not parsed.hostname:
            continue
        result.append({'url': link, 'title': title, 'company': board_token,
                       'location': location, 'country': '', 'work_mode': '',
                       'description': re.sub('<[^>]+>', ' ', item.get('content') or '')})
    return result
