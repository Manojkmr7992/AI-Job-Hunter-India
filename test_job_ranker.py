"""Automated tests for weighted job relevance ranking."""

import pytest

from job_classifier import load_taxonomy
from job_ranker import (
    rank_job,
    rank_jobs,
    recommendation_band
)


@pytest.fixture
def strong_job():
    return {
        "title": "Senior Technical Product Owner",
        "company": "Barclays",
        "location": "Pune",
        "country": "India",
        "work_mode": "hybrid",
        "description": (
            "AML transaction monitoring, credit cards, "
            "SQL, AWS, Snowflake and product roadmap"
        )
    }


def test_perfect_score(strong_job):
    result = rank_job(strong_job)

    assert result["relevance_score"] == 100
    assert result["recommendation"] == "Excellent match"


def test_unknown_employer_score(strong_job):
    strong_job["company"] = "New FinTech Startup"

    result = rank_job(strong_job)

    assert result["relevance_score"] == 98
    assert result["recommendation"] == "Excellent match"
    assert result["known_employer"] is False


def test_medium_priority_employer(strong_job):
    strong_job["company"] = "Deloitte"

    result = rank_job(strong_job)

    assert result["relevance_score"] == 99


def test_junior_role_override(strong_job):
    strong_job["title"] = "Junior Business Analyst"

    result = rank_job(strong_job)

    assert result["recommendation"] == "Lower priority"


def test_outside_india_override(strong_job):
    strong_job["location"] = "London"
    strong_job["country"] = "United Kingdom"

    result = rank_job(strong_job)

    assert result["recommendation"] == "Outside target"


def test_unknown_role_override(strong_job):
    strong_job["title"] = "Senior Tax Consultant"

    result = rank_job(strong_job)

    assert result["recommendation"] == "Manual review"


def test_missing_bfsi_evidence(strong_job):
    strong_job["description"] = "SQL, AWS and product roadmap"

    result = rank_job(strong_job)

    assert result["recommendation"] == "Manual review"
    assert result["score_breakdown"]["bfsi_relevance"] == 15


def test_explainable_score(strong_job):
    result = rank_job(strong_job)

    assert sum(result["score_breakdown"].values()) == (
        result["relevance_score"]
    )


def test_component_score_limits(strong_job):
    result = rank_job(strong_job)

    for key, value in result["score_breakdown"].items():
        assert 0 <= value <= result["ranking_weights"][key]


@pytest.mark.parametrize(
    "score,expected",
    [
        (100, "Excellent match"),
        (85, "Excellent match"),
        (84.99, "Strong match"),
        (70, "Strong match"),
        (69.99, "Potential match"),
        (55, "Potential match"),
        (54.99, "Manual review"),
        (40, "Manual review"),
        (39.99, "Low relevance"),
        (0, "Low relevance")
    ]
)
def test_recommendation_thresholds(score, expected):
    assert recommendation_band(score) == expected


def test_no_jobs_discarded(strong_job):
    jobs = [
        strong_job,
        {**strong_job, "company": "Unknown FinTech"},
        {**strong_job, "title": "Junior Business Analyst"},
        {**strong_job, "country": "United Kingdom"}
    ]

    assert len(rank_jobs(jobs)) == len(jobs)


def test_ranking_order(strong_job):
    jobs = [
        {**strong_job, "country": "United Kingdom"},
        {**strong_job, "company": "Unknown FinTech"},
        strong_job
    ]

    results = rank_jobs(jobs)

    assert results[0]["canonical_company"] == "Barclays"
    assert results[0]["relevance_score"] == 100
    assert results[1]["relevance_score"] == 98
    assert results[2]["recommendation"] == "Outside target"


def test_empty_job_list():
    assert rank_jobs([]) == []


def test_empty_job_score():
    result = rank_job({})

    assert 0 <= result["relevance_score"] <= 100
    assert result["recommendation"] == "Manual review"


def test_configurable_weights(strong_job):
    taxonomy = load_taxonomy()

    taxonomy["ranking_weights"]["role_relevance"] = 35
    taxonomy["ranking_weights"]["employer_preference"] = 0

    strong_job["company"] = "Unknown FinTech"

    result = rank_job(strong_job, taxonomy)

    assert result["relevance_score"] == 100
    assert result["score_breakdown"]["role_relevance"] == 35
    assert result["score_breakdown"]["employer_preference"] == 0


def test_invalid_weight_keys(strong_job):
    taxonomy = load_taxonomy()

    taxonomy["ranking_weights"]["unexpected"] = (
        taxonomy["ranking_weights"].pop("location")
    )

    with pytest.raises(ValueError, match="Unexpected ranking"):
        rank_job(strong_job, taxonomy)


def test_input_job_not_modified(strong_job):
    original = strong_job.copy()

    rank_job(strong_job)

    assert strong_job == original
