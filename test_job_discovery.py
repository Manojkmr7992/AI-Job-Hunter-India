import csv
import io
import sqlite3
import pytest
from core import init_db, list_jobs
from job_discovery import parse_csv, normalize_job, import_jobs, greenhouse_jobs

RULES = {'target_titles':['Technical Product Owner'], 'cities':['Bengaluru'], 'country':'India', 'allow_remote_india':True}

def row(**kwargs):
    return dict(url='https://example.com/job/123', title='Technical Product Owner', company='Bank',
                location='Bangalore', country='IN', work_mode='Hybrid', **kwargs)

def test_normalize():
    j = normalize_job(row())
    assert (j['location'], j['country']) == ('Bengaluru', 'India')

def test_parse_csv():
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=row().keys()); w.writeheader(); w.writerow(row())
    assert parse_csv(s.getvalue().encode('utf-8'))[0]['title'] == 'Technical Product Owner'

def test_missing_csv_headers():
    with pytest.raises(ValueError): parse_csv(b'title,url\na,b\n')

def test_csv_limit():
    with pytest.raises(ValueError): parse_csv(b'x' * 3_000_001)

def test_import_and_dedupe(tmp_path):
    db = tmp_path / 'jobs.sqlite3'; init_db(db)
    r = import_jobs([row(), row()], RULES, path=db)
    assert r['saved_or_updated'] == 1 and r['duplicates_in_file'] == 1
    assert len(list_jobs(db)) == 1

def test_exclude_other_city(tmp_path):
    db = tmp_path / 'jobs.sqlite3'; init_db(db)
    j = row(); j['location'] = 'Mumbai'
    r = import_jobs([j], RULES, path=db)
    assert r['excluded'] == 1 and not list_jobs(db)

def test_bad_url(tmp_path):
    db = tmp_path / 'jobs.sqlite3'; init_db(db)
    j = row(); j['url'] = 'javascript:alert(1)'
    r = import_jobs([j], RULES, path=db)
    assert len(r['errors']) == 1

def test_invalid_board_token():
    with pytest.raises(ValueError): greenhouse_jobs('../secret')
