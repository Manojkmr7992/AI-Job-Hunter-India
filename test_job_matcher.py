from pathlib import Path
import pytest
from candidate_profile import load_profile
from job_matcher import analyze_job

PROFILE = load_profile(Path(__file__).resolve().parent / "tests" / "fixtures" / "candidate_profile.json")

def test_po_role():
    r = analyze_job('Technical Product Owner', 'Banking, Snowflake, SQL, Scrum, product roadmap, user stories', PROFILE)
    assert r['recommended_resume'] == 'po'
    assert r['score'] == 100

def test_bsa_role():
    r = analyze_job('Technical Business Analyst', 'REST API, JSON, Postman, Kafka', PROFILE)
    assert r['recommended_resume'] == 'bsa'
    assert r['score'] == 100

def test_self_reported_discounted():
    r = analyze_job('Data Product Owner', 'Databricks and MySQL', PROFILE)
    assert r['score'] == 25
    assert all(x['status'] == 'self_reported' for x in r['evidence'])

def test_missing_skill():
    r = analyze_job('Technical Product Owner', 'OAuth integration', PROFILE)
    assert r['score'] == 25

def test_no_keywords():
    r = analyze_job('Mystery position', 'Something completely unrelated', PROFILE)
    assert r['requirements_found'] == 0 and r['score'] == 0

def test_invalid_description():
    with pytest.raises(ValueError):
        analyze_job('Technical Product Owner', '  ', PROFILE)

def test_word_boundaries():
    r = analyze_job('Technical Product Owner', 'snowflakes are pretty', PROFILE)
    assert 'Snowflake' not in [x['requirement'] for x in r['evidence']]
