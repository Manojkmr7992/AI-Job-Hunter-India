from core import SAMPLE_JOBS, add_job, evaluate, init_db, list_jobs, load_rules, update_status


def test_location_matching():
    rules = load_rules()
    assert evaluate(SAMPLE_JOBS[0], rules)[0]
    assert evaluate(SAMPLE_JOBS[1], rules)[0]
    assert not evaluate(SAMPLE_JOBS[2], rules)[0]
    assert not evaluate(SAMPLE_JOBS[3], rules)[0]


def test_database(tmp_path):
    db = tmp_path / "test.sqlite3"
    init_db(db)
    add_job(SAMPLE_JOBS[0], db)
    add_job(SAMPLE_JOBS[0], db)
    jobs = list_jobs(db)
    assert len(jobs) == 1
    update_status(jobs[0]["id"], "applied", db)
    assert list_jobs(db)[0]["status"] == "applied"
