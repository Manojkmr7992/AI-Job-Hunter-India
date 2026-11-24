"""Rules, validation and SQLite persistence for AI Job Hunter India."""
import json
import sqlite3
import os
from postgres_store import postgres_enabled, pg_init_db, pg_add_job, pg_list_jobs, pg_update_status
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "jobs.sqlite3"


def load_rules(path=None):
    return json.loads(Path(path or ROOT / "rules.json").read_text(encoding="utf-8"))


def evaluate(job, rules):
    """Return (eligible, explanation). This is intentionally strict and simple."""
    from job_classifier import (
        contains_phrase,
        classify_seniority
    )

    title = job["title"]

    seniority = classify_seniority(
        title,
        job.get("description", "")
    )

    if seniority["seniority"] == "lower_priority":
        return False, "Junior or entry-level role"

    if not any(
        contains_phrase(title, target)
        for target in rules["target_titles"]
    ):
        return False, "Title does not match target roles"
    city = job["location"].casefold()
    mode = job["work_mode"].casefold()
    if mode == "remote" and rules["allow_remote_india"] and job["country"].casefold() == "india":
        return True, "Remote India role"
    if job["country"].casefold() != rules["country"].casefold():
        return False, "Outside India"
    if any(allowed.casefold() == city for allowed in rules["cities"]):
        return True, "Preferred city"
    return False, "Outside preferred locations"


def init_db(path=DB_PATH):
    if path == DB_PATH and postgres_enabled():
        return pg_init_db()
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            country TEXT NOT NULL,
            work_mode TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'discovered'
        )""")


def add_job(job, path=DB_PATH):
    required = ("url", "title", "company", "location", "country", "work_mode")
    if any(not isinstance(job.get(k), str) or not job[k].strip() for k in required):
        raise ValueError("Every job must have a nonempty URL, title, company, location, country and work mode")
    parsed = urlsplit(job["url"])
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Job URL must be HTTP(S)")
    if job["work_mode"].casefold() not in ("remote", "hybrid", "onsite"):
        raise ValueError("work_mode must be Remote, Hybrid or Onsite")
    if path == DB_PATH and postgres_enabled():
        return pg_add_job(job)
    with sqlite3.connect(path) as db:
        db.execute("""INSERT INTO jobs(url,title,company,location,country,work_mode)
                      VALUES(?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET
                      title=excluded.title, company=excluded.company,
                      location=excluded.location, country=excluded.country,
                      work_mode=excluded.work_mode""", tuple(job[k].strip() for k in required))


def list_jobs(path=DB_PATH):
    if path == DB_PATH and postgres_enabled():
        return pg_list_jobs()
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY id DESC")]


def update_status(job_id, status, path=DB_PATH):
    if status not in ("discovered", "applied", "interview", "offer", "rejected", "skipped"):
        raise ValueError("Invalid application status")
    if path == DB_PATH and postgres_enabled():
        return pg_update_status(job_id, status)
    with sqlite3.connect(path) as db:
        result = db.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        if result.rowcount == 0:
            raise ValueError("Job not found")


SAMPLE_JOBS = [
    {"url": "https://example.com/demo/po-1", "title": "Senior Product Owner", "company": "Demo Bank", "location": "Bengaluru", "country": "India", "work_mode": "Hybrid"},
    {"url": "https://example.com/demo/pm-2", "title": "AI Product Manager", "company": "Demo Tech", "location": "Jaipur", "country": "India", "work_mode": "Remote"},
    {"url": "https://example.com/demo/ba-3", "title": "Junior Business Analyst", "company": "Demo Services", "location": "Hyderabad", "country": "India", "work_mode": "Onsite"},
    {"url": "https://example.com/demo/po-4", "title": "Technical Product Owner", "company": "Demo Finance", "location": "Mumbai", "country": "India", "work_mode": "Onsite"},
]
