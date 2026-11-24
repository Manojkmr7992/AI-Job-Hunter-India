"""Integrate live ATS discovery with existing job intelligence."""

from __future__ import annotations

from collections import Counter

from job_classifier import (
    load_taxonomy,
    classify_role,
    classify_seniority,
)

from core import load_rules, list_jobs
from live_job_discovery import discover_live_jobs
from smart_discovery import preview_jobs


def rank_live_discovery(
    discovery,
    existing=None,
    rules=None,
):
    """Rank India-matched jobs without database writes."""

    if existing is None:
        existing = list_jobs()

    if rules is None:
        rules = load_rules()

    taxonomy = load_taxonomy()

    india_candidates = discovery["india_jobs"]

    incoming = []
    suppressed_roles = []
    suppressed_seniority = []

    for job in india_candidates:

        title = job.get("title", "")
        description = job.get("description", "")

        role = classify_role(title, taxonomy)

        if not role.get("primary_role"):
            suppressed_roles.append(job)
            continue

        seniority = classify_seniority(
            title,
            description,
            taxonomy=taxonomy,
        )

        if seniority["seniority"] == "lower_priority":
            suppressed_seniority.append(job)
            continue

        incoming.append(job)

    results = preview_jobs(
        incoming,
        existing,
        rules,
    )

    # Preserve original row identity and source metadata.
    for result in results:

        original = incoming[result["row"] - 1]

        for field in (
            "source_provider",
            "source_board_id",
            "source_job_id",
            "original_location",
        ):
            result[field] = original.get(field, "")

    ranked = sorted(
        results,
        key=lambda result: (
            result["decision"] != "Eligible",
            -result["relevance_score"],
            result["row"],
        ),
    )

    decisions = Counter(
        result["decision"]
        for result in results
    )

    eligible_recommendations = Counter(
        result["recommendation"]
        for result in results
        if result["decision"] == "Eligible"
    )

    role_matches = [
        result
        for result in ranked
        if result.get("primary_role")
    ]

    summary = {
        **discovery["summary"],
        "ranked_jobs": len(results),
        "india_candidates_screened": len(india_candidates),
        "suppressed_unrelated_roles": len(suppressed_roles),
        "suppressed_junior_roles": len(suppressed_seniority),
        "screening_retained": len(incoming),
        "target_role_matches": len(role_matches),
        "eligible": decisions["Eligible"],
        "excluded": decisions["Excluded"],
        "duplicate_url": decisions["Duplicate URL"],
        "possible_duplicate": decisions["Possible duplicate"],
        "review": decisions["Review"],
        "excellent_matches":
            eligible_recommendations["Excellent match"],
        "strong_matches":
            eligible_recommendations["Strong match"],
        "potential_matches":
            eligible_recommendations["Potential match"],
        "manual_review_matches":
            eligible_recommendations["Manual review"],
        "low_relevance_matches":
            eligible_recommendations["Low relevance"],
    }

    return {
        "incoming": incoming,
        "india_candidates": india_candidates,
        "suppressed_roles": suppressed_roles,
        "suppressed_seniority": suppressed_seniority,
        "results": results,
        "ranked_results": ranked,
        "target_role_results": role_matches,
        "sources": discovery["sources"],
        "summary": summary,
    }


def discover_and_rank(
    config=None,
    board_ids=None,
    fetcher=None,
    existing=None,
    rules=None,
):
    """Execute live discovery and ranking in one operation."""

    discovery = discover_live_jobs(
        config=config,
        board_ids=board_ids,
        fetcher=fetcher,
    )

    return rank_live_discovery(
        discovery,
        existing=existing,
        rules=rules,
    )
