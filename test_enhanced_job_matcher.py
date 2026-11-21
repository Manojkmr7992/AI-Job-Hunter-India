"""Step 5.4 enhanced matcher integration tests."""

from copy import deepcopy

from job_matcher import analyze_job


def make_profile():
    return {
        "schema_version": 1,
        "name": "Test Candidate",
        "professional_headline": "Technical Product Owner",
        "experience_summary": "Banking product delivery",
        "resume_preference": {
            "primary": "po",
            "secondary": "bsa",
        },
        "target_roles": {
            "po": ["Product Owner"],
            "bsa": ["Business Analyst"],
        },
        "search_preferences": {
            "preferred_cities": ["Hyderabad"],
            "remote_india": True,
            "minimum_match_score": 60,
        },
        "domains": [],
        "certifications": [],
        "experience": [],
        "skills": [
            {
                "name": "Python",
                "category": "Technical",
                "evidence": "resume_documented",
                "proficiency": "professional_experience",
                "sources": ["po"],
            },
            {
                "name": "Snowflake",
                "category": "Technical",
                "evidence": "self_reported",
                "proficiency": "basic",
                "sources": [],
            },
        ],
    }


def test_weighted_score_and_missing_required():
    result = analyze_job(
        "Technical Product Owner",
        "Required Qualifications:\n"
        "- Python\n"
        "- SQL\n"
        "Preferred Qualifications:\n"
        "- Snowflake\n",
        make_profile(),
    )

    assert result["requirements_found"] == 3
    assert result["missing_required"] == ["SQL"]
    assert result["weighted_score"] == 46
    assert result["score"] == 42


def test_required_classification_in_enhanced_evidence():
    result = analyze_job(
        "Product Owner",
        "Required Qualifications:\n- Python\n",
        make_profile(),
    )

    assert result["enhanced_evidence"][0]["classification"] == "required"
    assert result["weighted_score"] == 100


def test_no_detected_requirements():
    result = analyze_job(
        "Product Owner",
        "Join our collaborative team.",
        make_profile(),
    )

    assert result["weighted_score"] == 0
    assert result["missing_required"] == []
    assert result["enhanced_evidence"] == []


def test_original_profile_is_not_mutated():
    profile = make_profile()
    original = deepcopy(profile)

    analyze_job(
        "Product Owner",
        "Required Qualifications:\n- Python\n",
        profile,
    )

    assert profile == original
