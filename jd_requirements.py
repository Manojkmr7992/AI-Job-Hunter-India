"""Step 5.4: explainable JD requirement classification."""

from __future__ import annotations

import re

from job_matcher import ALIASES, _contains

REQUIRED_HEADINGS = (
    "requirements",
    "required qualifications",
    "minimum qualifications",
    "must have",
    "must-have skills",
    "essential skills",
)

PREFERRED_HEADINGS = (
    "preferred qualifications",
    "preferred skills",
    "nice to have",
    "nice-to-have skills",
    "desired qualifications",
)

ALL_HEADINGS = set(REQUIRED_HEADINGS + PREFERRED_HEADINGS)


def _heading_type(line: str) -> str | None:
    normalized = re.sub(r"\s+", " ", line.strip().rstrip(":")).casefold()

    if normalized in REQUIRED_HEADINGS:
        return "required"
    if normalized in PREFERRED_HEADINGS:
        return "preferred"
    return None


def extract_requirements(description: str) -> list[dict]:
    """Extract known skills and classify explicit JD sections.

    A skill outside recognized sections remains unspecified.
    If the same skill appears in required and preferred sections,
    required takes precedence.
    """
    if not isinstance(description, str):
        raise TypeError("description must be a string")

    if not description.strip():
        return []

    found = {}
    current_section = "unspecified"
    priority = {"unspecified": 0, "preferred": 1, "required": 2}

    for line in description.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        heading = _heading_type(stripped)
        if heading is not None:
            current_section = heading
            continue

        for skill, aliases in ALIASES.items():
            if any(_contains(stripped, alias) for alias in aliases):
                previous = found.get(skill)

                if previous is None or priority[current_section] > priority[previous]:
                    found[skill] = current_section

    return [
        {"requirement": skill, "classification": classification}
        for skill, classification in found.items()
    ]
