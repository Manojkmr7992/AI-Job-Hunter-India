from controlled_import import import_approved

RULES = {'target_titles': ['Technical Product Owner'], 'cities': ['Bengaluru'],
         'country': 'India', 'allow_remote_india': True}

def job(url='https://example.com/1', **kwargs):
    d = {'url': url, 'title': 'Technical Product Owner', 'company': 'Demo Bank',
         'location': 'Bengaluru', 'country': 'India', 'work_mode': 'Hybrid'}
    d.update(kwargs)
    return d

def test_only_approved_rows_saved():
    saved = []
    jobs = [job(), job('https://example.com/2', company='Another Bank')]
    r = import_approved(jobs, [2], RULES, existing=[], save=saved.append)
    assert r['imported'] == 1 and saved == [jobs[1]] and r['skipped_unselected'] == 1

def test_existing_url_never_overwritten():
    saved = []
    r = import_approved([job(url='https://example.com/1?utm_source=x')], [1], RULES,
                        existing=[job()], save=saved.append)
    assert r['duplicate_url'] == 1 and not saved

def test_semantic_duplicate_blocked():
    saved = []
    r = import_approved([job('https://different.com/9')], [1], RULES,
                        existing=[job()], save=saved.append)
    assert r['possible_duplicate'] == 1 and not saved

def test_repeated_upload_rows_not_imported_twice():
    saved = []
    r = import_approved([job(), job()], [1, 2], RULES, existing=[], save=saved.append)
    assert r['imported'] == 1 and r['duplicate_url'] == 1 and len(saved) == 1

def test_excluded_blocked_even_when_selected():
    saved = []
    r = import_approved([job(location='Mumbai')], [1], RULES, existing=[], save=saved.append)
    assert r['excluded'] == 1 and not saved

def test_incomplete_blocked():
    r = import_approved([job(work_mode='')], [1], RULES, existing=[], save=lambda _: None)
    assert r['review'] == 1

def test_invalid_selections():
    import pytest
    for choices in ([0], [2], [1, 1], ['1']):
        with pytest.raises(ValueError):
            import_approved([job()], choices, RULES, existing=[], save=lambda _: None)

def test_save_failure_is_reported():
    def fail(_):
        raise RuntimeError('database unavailable')
    r = import_approved([job()], [1], RULES, existing=[], save=fail)
    assert r['imported'] == 0 and len(r['errors']) == 1
