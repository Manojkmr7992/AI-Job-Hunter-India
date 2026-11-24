"""Configuration-driven job relevance ranking engine."""

from job_classifier import (
    load_taxonomy,
    classify_job
)

PRIMARY_ROLES = {
    "product_ownership",
    "product_management",
    "business_systems_analysis",
    "data_products",
    "ai_products",
    "banking_leadership"
}

DIRECT_BFSI_EMPLOYERS = {
    "global_bank",
    "indian_bank",
    "payments",
    "fintech",
    "banking_technology",
    "financial_services"
}

EXPECTED_WEIGHTS = {
    "role_relevance",
    "bfsi_relevance",
    "seniority",
    "skills_relevance",
    "location",
    "employer_preference"
}


def recommendation_band(score):
    """Convert a numerical score to a recommendation."""

    if score >= 85:
        return "Excellent match"

    if score >= 70:
        return "Strong match"

    if score >= 55:
        return "Potential match"

    if score >= 40:
        return "Manual review"

    return "Low relevance"


def rank_job(job, taxonomy=None):
    """Calculate explainable job relevance out of 100."""

    taxonomy = taxonomy or load_taxonomy()

    weights = taxonomy["ranking_weights"]

    if set(weights) != EXPECTED_WEIGHTS:
        raise ValueError("Unexpected ranking weight keys")

    classification = classify_job(job, taxonomy)

    # 1. Role relevance
    primary_role = classification["primary_role"]

    if primary_role in PRIMARY_ROLES:
        role_factor = 1.0

    elif primary_role is not None:
        role_factor = 0.8

    else:
        role_factor = 0.0

    # 2. BFSI relevance
    if classification["bfsi_domains"]:
        bfsi_factor = 1.0

    elif (
        classification["company_category"]
        in DIRECT_BFSI_EMPLOYERS
    ):
        bfsi_factor = 0.6

    else:
        bfsi_factor = 0.0

    # 3. Seniority
    seniority_factor = {
        "preferred": 1.0,
        "review": 0.5,
        "lower_priority": 0.0
    }.get(classification["seniority"], 0.0)

    # 4. Technical and functional skills
    # Three distinct skill categories receive full points.
    skill_count = len(
        classification["skill_categories"]
    )

    skills_factor = min(skill_count / 3, 1.0)

    # 5. Location preference
    location_factor = {
        "preferred": 1.0,
        "review": 0.5,
        "outside_preferred_cities": 0.0,
        "outside_target": 0.0
    }.get(classification["location_status"], 0.0)

    # 6. Employer preference
    # Unknown employers retain a neutral baseline.
    employer_factor = {
        "high": 1.0,
        "medium": 0.8,
        "low": 0.6,
        None: 0.6
    }.get(classification["company_priority"], 0.6)

    factors = {
        "role_relevance": role_factor,
        "bfsi_relevance": bfsi_factor,
        "seniority": seniority_factor,
        "skills_relevance": skills_factor,
        "location": location_factor,
        "employer_preference": employer_factor
    }

    breakdown = {
        key: round(weights[key] * factor, 2)
        for key, factor in factors.items()
    }

    score = round(sum(breakdown.values()), 2)

    recommendation = recommendation_band(score)

    # Recommendation overrides preserve business rules.
    if classification["location_status"] == "outside_target":
        recommendation = "Outside target"

    elif classification["seniority"] == "lower_priority":
        recommendation = "Lower priority"

    elif classification["classification_status"] == "review":
        recommendation = "Manual review"

    return {
        **classification,
        "relevance_score": score,
        "maximum_score": 100,
        "score_breakdown": breakdown,
        "ranking_weights": dict(weights),
        "recommendation": recommendation
    }


def rank_jobs(jobs, taxonomy=None):
    """Rank opportunities without discarding any records."""

    taxonomy = taxonomy or load_taxonomy()

    ranked = [
        rank_job(job, taxonomy)
        for job in jobs
    ]

    recommendation_order = {
        "Excellent match": 0,
        "Strong match": 1,
        "Potential match": 2,
        "Manual review": 3,
        "Low relevance": 4,
        "Lower priority": 5,
        "Outside target": 6
    }

    return sorted(
        ranked,
        key=lambda job: (
            recommendation_order.get(
                job["recommendation"], 99
            ),
            -job["relevance_score"]
        )
    )
