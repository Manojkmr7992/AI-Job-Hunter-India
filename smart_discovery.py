"""Step 5.1: explainable, read-only job discovery screening."""
from __future__ import annotations
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from core import evaluate
from job_discovery import normalize_job
from job_classifier import load_taxonomy
from job_ranker import rank_job

TRACKING_PREFIXES = ('utm_',)
TRACKING_KEYS = {'ref', 'source', 'src', 'fbclid', 'gclid', 'sid', 'xp', 'px', 'nignbevent_src'}


def canonical_url(value: str) -> str:
    parsed = urlsplit((value or '').strip())
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
        return ''
    hostname = parsed.hostname.lower()
    netloc = hostname + (f':{parsed.port}' if parsed.port else '')
    path = parsed.path.rstrip('/') or '/'
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                             if k.lower() not in TRACKING_KEYS and not k.lower().startswith(TRACKING_PREFIXES)))
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ''))


def normalized_text(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').casefold()).strip()


def fingerprint(job: dict) -> tuple[str, str, str]:
    j = normalize_job(job)
    return (normalized_text(j['company']), normalized_text(j['title']), normalized_text(j['location']))


def preview_jobs(incoming: list[dict], existing: list[dict], rules: dict) -> list[dict]:
    """Never writes data. Ambiguous matches are flagged for human review."""
    urls = {u for job in existing if (u := canonical_url(job.get('url', '')))}
    fingerprints = {fingerprint(job) for job in existing}
    results = []
    taxonomy = load_taxonomy()

    for number, raw in enumerate(incoming, 1):
        job = normalize_job(raw)
        url = canonical_url(job['url'])
        key = fingerprint(job)
        missing = [field for field in ('url', 'title', 'company', 'location', 'country', 'work_mode')
                   if not job[field]]
        if missing or not url or job['work_mode'].casefold() not in ('hybrid', 'onsite', 'remote'):
            decision, reason = 'Review', 'Missing/invalid required fields or URL'
        elif url in urls:
            decision, reason = 'Duplicate URL', 'Already present or repeated URL'
        elif all(key) and key in fingerprints:
            decision, reason = 'Possible duplicate', 'Same company, title and location; check posting manually'
        else:
            eligible, reason = evaluate(job, rules)
            decision = 'Eligible' if eligible else 'Excluded'
        ranking = rank_job(job, taxonomy)

        results.append({
            **ranking,
            **job,
            'row': number,
            'decision': decision,
            'reason': reason
        })
        if url:
            urls.add(url)
        if all(key):
            fingerprints.add(key)
    return results
