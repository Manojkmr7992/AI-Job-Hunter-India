import copy
import json
import pytest
from candidate_profile import ProfileValidationError, choose_resume, load_profile, skills_by_evidence, validate_profile


def test_profile_loads_and_validates():
    profile = load_profile()
    assert profile["resume_preference"]["primary"] == "po"
    assert profile["resume_preference"]["secondary"] == "bsa"
    assert skills_by_evidence(profile, "resume_documented")
    assert skills_by_evidence(profile, "self_reported")


def test_resume_selection():
    profile = load_profile()
    assert choose_resume("Senior Technical Product Owner", profile) == "po"
    assert choose_resume("Technical Business Systems Analyst", profile) == "bsa"
    assert choose_resume("Unspecified Role", profile) == "po"


def test_rejects_invalid_evidence():
    profile = copy.deepcopy(load_profile())
    profile["skills"][0]["evidence"] = "verified"
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)


def test_rejects_falsely_sourced_self_reported_skill():
    profile = copy.deepcopy(load_profile())
    skill = next(s for s in profile["skills"] if s["evidence"] == "self_reported")
    skill["sources"] = ["po"]
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)
