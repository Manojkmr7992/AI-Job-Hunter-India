"""BFSI employer reference data and alias resolution."""

import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent
MASTER_PATH = ROOT / "company_master.json"

REQUIRED_FIELDS = {
    "company_id",
    "company_name",
    "aliases",
    "category",
    "priority",
    "target_country",
    "target_locations",
    "enabled",
    "career_url",
    "integration_status"
}


def normalize_company_name(name):
    """Normalize employer names for exact alias matching."""

    if not isinstance(name, str):
        raise ValueError("Company name must be a string")

    return re.sub(
        r"[\W_]+", "", name.casefold()
    )


def load_company_master(path=MASTER_PATH):
    """Load and validate company reference data."""

    with Path(path).open(encoding="utf-8") as file:
        master = json.load(file)

    if not isinstance(master, dict):
        raise ValueError("Company master must be an object")

    companies = master.get("companies")

    if not isinstance(companies, list):
        raise ValueError("Companies must be a list")

    seen_ids = set()
    seen_names = {}

    for company in companies:

        if not isinstance(company, dict):
            raise ValueError("Invalid company record")

        missing = REQUIRED_FIELDS - company.keys()

        if missing:
            raise ValueError(
                f"Missing fields: {sorted(missing)}"
            )

        string_fields = REQUIRED_FIELDS - {
            "aliases", "target_locations",
            "enabled", "career_url"
        }

        for field in string_fields:
            value = company[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid field: {field}")

        company_id = company["company_id"]

        if company_id in seen_ids:
            raise ValueError(
                f"Duplicate company ID: {company_id}"
            )

        seen_ids.add(company_id)

        if company["priority"] not in {
            "high", "medium", "low"
        }:
            raise ValueError("Invalid company priority")

        if not isinstance(company["enabled"], bool):
            raise ValueError("Invalid enabled flag")

        for field in ("aliases", "target_locations"):
            values = company[field]

            if not isinstance(values, list):
                raise ValueError(f"Invalid list: {field}")

            if not all(
                isinstance(v, str) and v.strip()
                for v in values
            ):
                raise ValueError(f"Invalid values: {field}")

        names = [
            company["company_name"],
            *company["aliases"]
        ]

        for name in names:
            normalized = normalize_company_name(name)

            if not normalized:
                raise ValueError("Empty normalized name")

            existing = seen_names.get(normalized)

            if existing and existing != company_id:
                raise ValueError(
                    f"Ambiguous company alias: {name}"
                )

            seen_names[normalized] = company_id

    return master


def get_companies(
    category=None,
    priority=None,
    enabled_only=False,
    path=MASTER_PATH
):
    """Retrieve companies using optional filters."""

    companies = load_company_master(path)["companies"]

    if category is not None:
        companies = [
            c for c in companies
            if c["category"] == category
        ]

    if priority is not None:
        companies = [
            c for c in companies
            if c["priority"] == priority
        ]

    if enabled_only:
        companies = [
            c for c in companies
            if c["enabled"]
        ]

    return companies


def resolve_company(name, path=MASTER_PATH):
    """Resolve an employer name to its canonical record."""

    normalized = normalize_company_name(name)

    if not normalized:
        return None

    for company in get_companies(path=path):

        names = [
            company["company_name"],
            *company["aliases"]
        ]

        if any(
            normalize_company_name(n) == normalized
            for n in names
        ):
            return company

    return None


def company_summary(path=MASTER_PATH):
    """Generate company master statistics."""

    companies = get_companies(path=path)

    return {
        "total_companies": len(companies),
        "enabled_companies": sum(
            c["enabled"] for c in companies
        ),
        "categories": dict(Counter(
            c["category"] for c in companies
        )),
        "priorities": dict(Counter(
            c["priority"] for c in companies
        ))
    }
