"""Regression tests for live job screening and ranking."""

from live_job_ranking import rank_live_discovery


def make_job(
    index,
    title,
    work_mode="Hybrid",
    description=None,
):
    return {
        "url": f"https://example.com/jobs/{index}",
        "title": title,
        "company": "Barclays",
        "location": "Hyderabad",
        "country": "India",
        "work_mode": work_mode,
        "description": (
            description
            if description is not None
            else (
                "AML transaction monitoring, payments, "
                "SQL, Snowflake, AWS, product roadmap "
                "and stakeholder management."
            )
        ),
        "source_provider": "greenhouse",
        "source_board_id": "test_board",
        "source_job_id": str(index),
        "original_location": "Hyderabad, India",
    }


def make_discovery(jobs):
    return {
        "jobs": jobs,
        "india_jobs": jobs,
        "sources": [],
        "summary": {
            "sources_attempted": 1,
            "sources_successful": 1,
            "sources_failed": 0,
            "total_jobs": len(jobs),
            "india_jobs": len(jobs),
            "unknown_country_jobs": 0,
            "india_missing_work_mode": sum(
                not job["work_mode"] for job in jobs
            ),
        },
    }


def rank(jobs, existing=None):
    return rank_live_discovery(
        make_discovery(jobs),
        existing=[] if existing is None else existing,
    )


def test_target_roles_retained():
    titles = [
        "Senior Technical Product Owner",
        "Staff Product Manager",
        "VP - Technology Product Management",
        "Lead Business Systems Analyst",
        "AI Product Manager",
        "Data Product Owner",
    ]

    jobs = [
        make_job(i, title)
        for i, title in enumerate(titles, 1)
    ]

    report = rank(jobs)

    assert report["summary"]["screening_retained"] == 6
    assert report["summary"]["ranked_jobs"] == 6
    assert report["summary"]["suppressed_unrelated_roles"] == 0


def test_unrelated_roles_suppressed():
    titles = [
        "Software Engineer",
        "Machine Learning Engineer",
        "Principal Engineer",
        "Data Engineer",
        "AI Engineer",
        "Account Executive",
    ]

    jobs = [
        make_job(i, title)
        for i, title in enumerate(titles, 1)
    ]

    report = rank(jobs)

    assert report["summary"]["suppressed_unrelated_roles"] == 6
    assert report["results"] == []


def test_junior_roles_suppressed():
    jobs = [
        make_job(1, "Junior Business Analyst"),
        make_job(2, "Junior Product Owner"),
    ]

    report = rank(jobs)

    assert report["summary"]["suppressed_junior_roles"] == 2
    assert report["results"] == []


def test_unknown_seniority_retained():
    jobs = [
        make_job(
            1,
            "Product Manager",
            description="Product roadmap and payments.",
        )
    ]

    report = rank(jobs)

    assert report["summary"]["screening_retained"] == 1
    assert report["results"][0]["seniority"] == "review"


def test_screening_reconciliation():
    jobs = [
        make_job(1, "Senior Product Owner"),
        make_job(2, "Software Engineer"),
        make_job(3, "Junior Business Analyst"),
        make_job(4, "Lead Business Systems Analyst"),
    ]

    summary = rank(jobs)["summary"]

    assert summary["india_candidates_screened"] == 4
    assert summary["suppressed_unrelated_roles"] == 1
    assert summary["suppressed_junior_roles"] == 1
    assert summary["screening_retained"] == 2

    assert (
        summary["suppressed_unrelated_roles"]
        + summary["suppressed_junior_roles"]
        + summary["screening_retained"]
        == summary["india_candidates_screened"]
    )


def test_controlled_import_row_identity():
    jobs = [
        make_job(1, "Software Engineer"),
        make_job(2, "Senior Product Owner"),
        make_job(3, "Junior Business Analyst"),
        make_job(4, "Lead Business Systems Analyst"),
    ]

    report = rank(jobs)

    assert len(report["incoming"]) == 2

    for result in report["ranked_results"]:
        original = report["incoming"][result["row"] - 1]

        assert result["url"] == original["url"]
        assert result["title"] == original["title"]
        assert result["source_job_id"] == original["source_job_id"]


def test_source_metadata_preserved():
    job = make_job(1, "Senior Product Owner")

    result = rank([job])["results"][0]

    for field in [
        "source_provider",
        "source_board_id",
        "source_job_id",
        "original_location",
    ]:
        assert result[field] == job[field]


def test_empty_discovery():
    report = rank([])

    assert report["results"] == []
    assert report["incoming"] == []
    assert report["summary"]["screening_retained"] == 0
    assert report["summary"]["eligible"] == 0


def test_all_candidates_suppressed():
    jobs = [
        make_job(1, "Software Engineer"),
        make_job(2, "Junior Product Owner"),
    ]

    report = rank(jobs)

    assert report["results"] == []
    assert report["summary"]["suppressed_unrelated_roles"] == 1
    assert report["summary"]["suppressed_junior_roles"] == 1
    assert len(report["india_candidates"]) == 2


def test_duplicate_detection_preserved():
    job = make_job(1, "Senior Product Owner")

    report = rank([job], existing=[job])

    assert report["results"][0]["decision"] == "Duplicate URL"
    assert report["summary"]["duplicate_url"] == 1


def test_missing_work_mode_requires_review():
    job = make_job(
        1,
        "Senior Product Owner",
        work_mode="",
    )

    report = rank([job])

    assert report["summary"]["screening_retained"] == 1
    assert report["results"][0]["decision"] == "Review"


def test_original_candidates_preserved_on_reranking():
    jobs = [
        make_job(1, "Senior Product Owner"),
        make_job(2, "Software Engineer"),
        make_job(3, "Junior Product Owner"),
    ]

    initial = rank(jobs)

    refreshed = rank_live_discovery(
        {
            "india_jobs": initial["india_candidates"],
            "sources": initial["sources"],
            "summary": initial["summary"],
        },
        existing=[],
    )

    for key in [
        "india_candidates_screened",
        "suppressed_unrelated_roles",
        "suppressed_junior_roles",
        "screening_retained",
    ]:
        assert refreshed["summary"][key] == initial["summary"][key]

    assert len(refreshed["india_candidates"]) == 3
