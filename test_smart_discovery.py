from smart_discovery import canonical_url, fingerprint, preview_jobs

RULES = {'target_titles': ['Technical Product Owner'], 'cities': ['Bengaluru'],
         'country': 'India', 'allow_remote_india': True}

def job(url='https://example.com/jobs/123', **changes):
    value = dict(url=url, title='Technical Product Owner', company='Demo Bank',
                 location='Bangalore', country='IN', work_mode='Hybrid')
    value.update(changes)
    return value

def test_url_tracking_removed():
    assert canonical_url('https://EXAMPLE.com/jobs/123/?utm_source=email&src=alert') == 'https://example.com/jobs/123'

def test_url_rejects_unsafe():
    assert canonical_url('javascript:alert(1)') == ''

def test_normalized_fingerprint():
    assert fingerprint(job()) == fingerprint(job(location='Bengaluru', company='DEMO BANK'))

def test_duplicate_url():
    result = preview_jobs([job(url='https://example.com/jobs/123?utm_source=mail')], [job()], RULES)
    assert result[0]['decision'] == 'Duplicate URL'

def test_possible_duplicate():
    result = preview_jobs([job(url='https://other.example/jobs/456')], [job()], RULES)
    assert result[0]['decision'] == 'Possible duplicate'

def test_eligible():
    assert preview_jobs([job()], [], RULES)[0]['decision'] == 'Eligible'

def test_excluded():
    assert preview_jobs([job(location='Mumbai')], [], RULES)[0]['decision'] == 'Excluded'

def test_missing_work_mode_review():
    assert preview_jobs([job(work_mode='')], [], RULES)[0]['decision'] == 'Review'

def test_repeated_in_upload():
    results = preview_jobs([job(), job()], [], RULES)
    assert [r['decision'] for r in results] == ['Eligible', 'Duplicate URL']
