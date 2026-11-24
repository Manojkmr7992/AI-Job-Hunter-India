"""Integration tests for screened live job imports."""

from core import load_rules
from controlled_import import import_approved
from live_job_ranking import rank_live_discovery


def make_job(index, title, work_mode="Hybrid"):
    return {
        "url": f"https://example.com/live/{index}",
        "title": title,
        "company": "Barclays",
        "location": "Hyderabad",
        "country": "India",
        "work_mode": work_mode,
        "description": (
            "AML transaction monitoring, payments, "
            "SQL, AWS, Snowflake and product roadmap."
        ),
        "source_provider": "greenhouse",
        "source_board_id": "test_board",
        "source_job_id": str(index),
        "original_location": "Hyderabad, India",
    }


def make_report():
    jobs = [
        make_job(1, "Software Engineer"),
        make_job(2, "Senior Technical Product Owner"),
        make_job(3, "Junior Business Analyst"),
        make_job(4, "Lead Business Systems Analyst"),
        make_job(5, "Senior Product Manager", ""),
    ]

    return rank_live_discovery(
        {
            "india_jobs": jobs,
            "sources": [],
            "summary": {
                "sources_attempted": 1,
                "sources_successful": 1,
                "sources_failed": 0,
                "total_jobs": 5,
                "india_jobs": 5,
                "unknown_country_jobs": 0,
                "india_missing_work_mode": 1,
            },
        },
        existing=[],
    )


def test_import_correct_screened_record():
    report = make_report()
    saved = []

    def fake_save(job):
        saved.append(dict(job))

    result = import_approved(
        report["incoming"],
        [1],
        load_rules(),
        existing=[],
        save=fake_save,
    )

    assert result["imported"] == 1
    assert len(saved) == 1
    assert saved[0]["url"] == "https://example.com/live/2"
    assert saved[0]["title"] == "Senior Technical Product Owner"


def test_unselected_jobs_not_imported():
    report = make_report()
    saved = []

    result = import_approved(
        report["incoming"],
        [2],
        load_rules(),
        existing=[],
        save=lambda job: saved.append(dict(job)),
    )

    assert result["imported"] == 1
    assert len(saved) == 1
    assert saved[0]["url"] == "https://example.com/live/4"


def test_review_record_cannot_be_imported():
    report = make_report()
    saved = []

    result = import_approved(
        report["incoming"],
        [3],
        load_rules(),
        existing=[],
        save=lambda job: saved.append(dict(job)),
    )

    assert result["imported"] == 0
    assert result["review"] == 1
    assert saved == []


def test_duplicate_record_cannot_be_imported():
    report = make_report()
    saved = []

    result = import_approved(
        report["incoming"],
        [1],
        load_rules(),
        existing=[report["incoming"][0]],
        save=lambda job: saved.append(dict(job)),
    )

    assert result["imported"] == 0
    assert result["duplicate_url"] == 1
    assert saved == []


def test_no_selection_means_no_import():
    report = make_report()
    saved = []

    result = import_approved(
        report["incoming"],
        [],
        load_rules(),
        existing=[],
        save=lambda job: saved.append(dict(job)),
    )

    assert result["imported"] == 0
    assert saved == []


def test_reranking_after_successful_import():
    report = make_report()
    saved = []

    result = import_approved(
        report["incoming"],
        [1],
        load_rules(),
        existing=[],
        save=lambda job: saved.append(dict(job)),
    )

    assert result["imported"] == 1

    refreshed = rank_live_discovery(
        {
            "india_jobs": report["india_candidates"],
            "sources": report["sources"],
            "summary": report["summary"],
        },
        existing=saved,
    )

    assert refreshed["summary"]["duplicate_url"] == 1
    assert refreshed["summary"]["india_candidates_screened"] == 5
    assert refreshed["summary"]["suppressed_unrelated_roles"] == 1
    assert refreshed["summary"]["suppressed_junior_roles"] == 1
    assert refreshed["summary"]["screening_retained"] == 3

    imported_job = next(
        job
        for job in refreshed["results"]
        if job["url"] == saved[0]["url"]
    )

    assert imported_job["decision"] == "Duplicate URL"
