"""Portable Step 5.4 Streamlit UI tests."""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).resolve().parent / "pages" / "2_Job_Matcher.py"


def fake_profile():
    return {
        "schema_version": 1,
        "name": "Test Candidate",
        "professional_headline": "Technical Product Owner",
        "experience_summary": "Synthetic test profile",
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
            }
        ],
    }


def run_page():
    with patch(
        "candidate_profile.load_profile",
        return_value=fake_profile(),
    ):
        return AppTest.from_file(str(PAGE)).run()


def test_job_matcher_page_loads():
    at = run_page()

    assert not at.exception
    assert any(
        "Enhanced Job Description Matcher" in item.value
        for item in at.title
    )


def test_job_matcher_has_inputs():
    at = run_page()

    assert not at.exception
    assert len(at.text_input) >= 1
    assert len(at.text_area) >= 1
    assert len(at.button) >= 1
