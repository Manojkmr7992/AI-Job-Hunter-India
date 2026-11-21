"""Step 5.3: explainable BFSI relevance assessment; never bypasses eligibility."""
from __future__ import annotations
import re
from core import evaluate
from job_discovery import normalize_job

DOMAIN_TERMS = ('bank', 'banking', 'bfsi', 'fintech', 'financial services', 'payments',
                'credit card', 'cards', 'fraud', 'aml', 'anti money laundering',
                'risk', 'compliance', 'lending', 'loan', 'insurance')
DATA_TERMS = ('data', 'analytics', 'cloud', 'aws', 'snowflake', 'etl', 'platform',
              'ai', 'machine learning', 'ml', 'technical', 'api')
SENIOR_TERMS = ('senior', 'sr', 'lead', 'principal', 'staff', 'manager', 'head')
JUNIOR_TERMS = ('junior', 'jr', 'associate', 'intern', 'graduate', 'entry level')


def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, re.I))


def assess_job(job: dict, rules: dict) -> dict:
    """Return eligibility, 0–100 ranking and auditable reasons.

    Missing description never causes an exclusion. Title/location/country rules
    remain authoritative; a high relevance score cannot override them.
    """
    clean = normalize_job(job)
    eligible, eligibility_reason = evaluate(clean, rules)
    title = clean['title']
    context = ' '.join(str(job.get(k) or '') for k in ('title', 'company', 'description'))
    domain_hits = [term for term in DOMAIN_TERMS if _contains(context, term)]
    data_hits = [term for term in DATA_TERMS if _contains(context, term)]
    senior_hits = [term for term in SENIOR_TERMS if _contains(title, term)]
    junior_hits = [term for term in JUNIOR_TERMS if _contains(title, term)]
    reasons = []
    score = 0
    if any(_contains(title, term) for term in rules['target_titles']):
        score += 40
        reasons.append('Target product role')
    if domain_hits:
        score += min(25, 10 + 5 * len(domain_hits))
        reasons.append('BFSI signals: ' + ', '.join(domain_hits[:4]))
    else:
        reasons.append('BFSI domain not established by available text')
    if data_hits:
        score += min(20, 5 * len(data_hits))
        reasons.append('Technical/data signals: ' + ', '.join(data_hits[:4]))
    if senior_hits:
        score += 10
        reasons.append('Senior-level title signal')
    if junior_hits:
        score -= 20
        reasons.append('Junior-level title signal')
    if clean['country'].casefold() == rules['country'].casefold():
        if clean['location'].casefold() in {c.casefold() for c in rules['cities']}:
            score += 5
            reasons.append('Preferred city')
        elif clean['work_mode'].casefold() == 'remote' and rules['allow_remote_india']:
            score += 5
            reasons.append('Remote India')
    score = max(0, min(100, score))
    if not eligible:
        tier = 'Excluded'
    elif score >= 75:
        tier = 'High match'
    elif score >= 55:
        tier = 'Good match'
    else:
        tier = 'Low evidence'
    return {'eligible': eligible, 'eligibility_reason': eligibility_reason,
            'score': score, 'match_tier': tier, 'reasons': reasons,
            'domain_signals': domain_hits, 'technical_signals': data_hits}
