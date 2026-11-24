"""Configuration-driven role and BFSI job classification."""

import json
import re
from pathlib import Path

from company_master import resolve_company

ROOT = Path(__file__).resolve().parent
TAXONOMY_PATH = ROOT / "job_taxonomy.json"

REQUIRED_SECTIONS = {
    "version",
    "country",
    "search_policy",
    "role_families",
    "seniority",
    "bfsi_domains",
    "technical_skills",
    "ranking_weights"
}


def normalize_text(value):
    """Normalize text for case-insensitive phrase matching."""

    return re.sub(
        r"[\W_]+",
        " ",
        str(value or "").casefold()
    ).strip()


def contains_phrase(text, phrase):
    """Match complete words and phrases."""

    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)

    if not normalized_phrase:
        return False

    return bool(re.search(
        r"\b" + re.escape(normalized_phrase) + r"\b",
        normalized_text
    ))


def load_taxonomy(path=TAXONOMY_PATH):
    """Load and validate job taxonomy configuration."""

    with Path(path).open(encoding="utf-8") as file:
        taxonomy = json.load(file)

    if not isinstance(taxonomy, dict):
        raise ValueError("Taxonomy must be a JSON object")

    missing = REQUIRED_SECTIONS - taxonomy.keys()

    if missing:
        raise ValueError(
            f"Missing taxonomy sections: {sorted(missing)}"
        )

    for section in (
        "role_families",
        "seniority",
        "bfsi_domains",
        "technical_skills"
    ):
        groups = taxonomy[section]

        if not isinstance(groups, dict) or not groups:
            raise ValueError(f"Invalid section: {section}")

        for group, phrases in groups.items():
            if not isinstance(phrases, list) or not phrases:
                raise ValueError(
                    f"Invalid phrase list: {group}"
                )

            if not all(
                isinstance(p, str) and normalize_text(p)
                for p in phrases
            ):
                raise ValueError(
                    f"Invalid phrase in group: {group}"
                )

    weights = taxonomy["ranking_weights"]

    if not isinstance(weights, dict):
        raise ValueError("Invalid ranking weights")

    if not all(
        type(w) in (int, float) and 0 <= w <= 100
        for w in weights.values()
    ):
        raise ValueError("Invalid ranking weight value")

    if sum(weights.values()) != 100:
        raise ValueError("Ranking weights must total 100")

    policy = taxonomy["search_policy"]

    if not isinstance(policy, dict):
        raise ValueError("Invalid search policy")

    if policy.get("restrict_to_company_master") is not False:
        raise ValueError(
            "Company whitelist restriction must be disabled"
        )

    if policy.get("allow_unknown_employers") is not True:
        raise ValueError("Unknown employers must be allowed")

    return taxonomy


def match_groups(text, groups):
    """Return matching categories and keyword evidence."""

    matches = {}

    for group, phrases in groups.items():

        matched = list(dict.fromkeys(
            phrase for phrase in phrases
            if contains_phrase(text, phrase)
        ))

        if matched:
            matches[group] = matched

    return matches


def classify_role(title, taxonomy=None):
    """Classify job title using configured role families."""

    taxonomy = taxonomy or load_taxonomy()

    matches = match_groups(
        title,
        taxonomy["role_families"]
    )

    if not matches:
        return {
            "primary_role": None,
            "matched_roles": {},
            "role_status": "review"
        }

    # Prefer the most specific matching title.
    primary = max(
        matches,
        key=lambda group: max(
            len(normalize_text(p).split())
            for p in matches[group]
        )
    )

    return {
        "primary_role": primary,
        "matched_roles": matches,
        "role_status": "matched"
    }


def classify_seniority(
    title,
    description="",
    taxonomy=None
):
    """Identify seniority without requiring a senior title."""

    taxonomy = taxonomy or load_taxonomy()
    groups = taxonomy["seniority"]

    matches = match_groups(title, groups)

    # Product Manager alone does not prove seniority.
    preferred = [
        p for p in matches.get("preferred", [])
        if normalize_text(p) != "manager"
    ]

    if matches.get("lower_priority"):
        level = "lower_priority"
        evidence = matches["lower_priority"]

    elif preferred:
        level = "preferred"
        evidence = preferred

    else:
        # Conservative experience-based evidence.
        experience = re.findall(
            r"\b(\d{1,2})\s*\+?\s*"
            r"years?\s+(?:of\s+)?"
            r"(?:relevant\s+|professional\s+)?"
            r"experience\b",
            str(description or ""),
            flags=re.IGNORECASE
        )

        years = [
            int(y) for y in experience
            if 0 < int(y) <= 50
        ]

        if years and max(years) >= 8:
            level = "preferred"
            evidence = [
                f"{max(years)} years experience"
            ]
        else:
            level = "review"
            evidence = matches.get("review", [])

    return {
        "seniority": level,
        "seniority_evidence": evidence
    }


def classify_bfsi(
    title,
    description="",
    taxonomy=None
):
    """Identify BFSI domains using title and JD evidence."""

    taxonomy = taxonomy or load_taxonomy()

    text = f"{title or ''} {description or ''}"

    matches = match_groups(
        text,
        taxonomy["bfsi_domains"]
    )

    return {
        "bfsi_domains": list(matches),
        "bfsi_evidence": matches,
        "bfsi_status": (
            "matched" if matches else "review"
        )
    }


def classify_skills(
    title,
    description="",
    taxonomy=None
):
    """Extract technical and functional skill evidence."""

    taxonomy = taxonomy or load_taxonomy()

    matches = match_groups(
        f"{title or ''} {description or ''}",
        taxonomy["technical_skills"]
    )

    return {
        "skill_categories": list(matches),
        "skill_evidence": matches
    }


def classify_employer(company_name):
    """Enrich known employers without rejecting unknown ones."""

    company = resolve_company(company_name or "")

    if company is None:
        return {
            "company_id": None,
            "canonical_company": company_name,
            "company_category": "unclassified",
            "company_priority": None,
            "known_employer": False
        }

    return {
        "company_id": company["company_id"],
        "canonical_company": company["company_name"],
        "company_category": company["category"],
        "company_priority": company["priority"],
        "known_employer": True
    }


def classify_location(job, taxonomy=None):
    """Identify preferred locations and remote India roles."""

    taxonomy = taxonomy or load_taxonomy()
    policy = taxonomy["search_policy"]

    location = job.get("location", "")
    country = normalize_text(job.get("country", ""))
    work_mode = normalize_text(job.get("work_mode", ""))

    india_confirmed = country in {"india", "in"}

    matches = [
        city
        for city in policy["target_locations"]
        if contains_phrase(location, city)
    ]

    if country and not india_confirmed:
        status = "outside_target"

    elif (
        india_confirmed
        and work_mode == "remote"
        and policy["allow_remote_india"]
    ):
        status = "preferred"

    elif matches:
        status = "preferred"

    elif india_confirmed and location:
        status = "outside_preferred_cities"

    else:
        status = "review"

    return {
        "location_status": status,
        "matched_locations": matches
    }


def classify_job(job, taxonomy=None):
    """Classify one normalized job opportunity."""

    taxonomy = taxonomy or load_taxonomy()

    title = job.get("title", "")
    description = job.get("description", "")
    company = job.get("company", "")

    result = {
        "title": title,
        "company": company
    }

    result.update(classify_role(title, taxonomy))

    result.update(classify_seniority(
        title, description, taxonomy
    ))

    result.update(classify_bfsi(
        title, description, taxonomy
    ))

    result.update(classify_skills(
        title, description, taxonomy
    ))

    result.update(classify_employer(company))

    result.update(classify_location(job, taxonomy))

    if result["location_status"] == "outside_target":
        status = "outside_target"

    elif result["seniority"] == "lower_priority":
        status = "lower_priority"

    elif (
        result["role_status"] == "matched"
        and result["bfsi_status"] == "matched"
        and result["seniority"] == "preferred"
        and result["location_status"] == "preferred"
    ):
        status = "relevant"

    else:
        status = "review"

    result["classification_status"] = status

    return result
