"""Candidate profile loading, schema validation and resume selection (stdlib only)."""
from __future__ import annotations

import json
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent / "candidate_profile.json"
ALLOWED_EVIDENCE = {"resume_documented", "self_reported"}
ALLOWED_PROFICIENCY = {
    "professional_experience", "platform_exposure", "integration_exposure",
    "requirements_experience", "tool_exposure", "basic", "unconfirmed",
}


class ProfileValidationError(ValueError):
    """Raised when candidate_profile.json does not follow the expected schema."""


def validate_profile(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise ProfileValidationError("Profile must be a JSON object")
    if profile.get("schema_version") != 1:
        raise ProfileValidationError("Unsupported schema_version (expected 1)")
    for field in ("name", "professional_headline", "experience_summary"):
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise ProfileValidationError(f"{field} must be a nonempty string")
    preference = profile.get("resume_preference")
    if not isinstance(preference, dict) or preference.get("primary") not in ("po", "bsa") or preference.get("secondary") not in ("po", "bsa"):
        raise ProfileValidationError("resume_preference must identify po and bsa")
    if preference["primary"] == preference["secondary"]:
        raise ProfileValidationError("Primary and secondary resumes must differ")
    roles = profile.get("target_roles")
    if not isinstance(roles, dict) or any(not isinstance(roles.get(k), list) or not roles[k] or not all(isinstance(r, str) and r.strip() for r in roles[k]) for k in ("po", "bsa")):
        raise ProfileValidationError("target_roles.po and target_roles.bsa must be nonempty string lists")
    search = profile.get("search_preferences")
    if not isinstance(search, dict) or not isinstance(search.get("preferred_cities"), list) or not isinstance(search.get("remote_india"), bool):
        raise ProfileValidationError("Invalid search_preferences")
    threshold = search.get("minimum_match_score")
    if type(threshold) not in (int, float) or not 0 <= threshold <= 100:
        raise ProfileValidationError("minimum_match_score must be between 0 and 100")
    for field in ("domains", "certifications"):
        if not isinstance(profile.get(field), list) or not all(isinstance(x, str) and x.strip() for x in profile[field]):
            raise ProfileValidationError(f"{field} must be a list of strings")
    if not isinstance(profile.get("experience"), list):
        raise ProfileValidationError("experience must be a list")
    skills = profile.get("skills")
    if not isinstance(skills, list) or not skills:
        raise ProfileValidationError("skills must be a nonempty list")
    names = set()
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            raise ProfileValidationError(f"skills[{index}] must be an object")
        for field in ("name", "category"):
            if not isinstance(skill.get(field), str) or not skill[field].strip():
                raise ProfileValidationError(f"skills[{index}].{field} is required")
        name = skill["name"].casefold()
        if name in names:
            raise ProfileValidationError(f"Duplicate skill: {skill['name']}")
        names.add(name)
        if skill.get("evidence") not in ALLOWED_EVIDENCE:
            raise ProfileValidationError(f"Invalid evidence for {skill['name']}")
        if skill.get("proficiency") not in ALLOWED_PROFICIENCY:
            raise ProfileValidationError(f"Invalid proficiency for {skill['name']}")
        sources = skill.get("sources")
        if not isinstance(sources, list) or any(s not in ("po", "bsa") for s in sources):
            raise ProfileValidationError(f"Invalid sources for {skill['name']}")
        if skill["evidence"] == "resume_documented" and not sources:
            raise ProfileValidationError(f"Resume-documented skill needs source: {skill['name']}")
        if skill["evidence"] == "self_reported" and sources:
            raise ProfileValidationError(f"Self-reported skill cannot claim resume source: {skill['name']}")
    return profile


def load_profile(path: str | Path = PROFILE_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return validate_profile(json.load(file))


def choose_resume(job_title: str, profile: dict) -> str:
    """Select PO or BSA using title signals; tie/unknown defaults to primary."""
    if not isinstance(job_title, str):
        raise TypeError("job_title must be a string")
    validate_profile(profile)
    title = job_title.casefold()
    po_signals = ("product owner", "product manager", "technical product manager", "tpm")
    bsa_signals = ("business analyst", "business systems analyst", "systems analyst", "system analyst", "product analyst", "bsa")
    po_score = sum(signal in title for signal in po_signals)
    bsa_score = sum(signal in title for signal in bsa_signals)
    return "bsa" if bsa_score > po_score else profile["resume_preference"]["primary"]


def skills_by_evidence(profile: dict, evidence: str) -> list[dict]:
    validate_profile(profile)
    if evidence not in ALLOWED_EVIDENCE:
        raise ValueError(f"Unknown evidence: {evidence}")
    return [skill for skill in profile["skills"] if skill["evidence"] == evidence]
