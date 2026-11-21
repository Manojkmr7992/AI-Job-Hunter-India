"""Tests for Step 5.4 requirement classification."""

import pytest

from jd_requirements import extract_requirements


def as_map(description):
    return {
        item["requirement"]: item["classification"]
        for item in extract_requirements(description)
    }


def test_required_and_preferred_sections():
    result = as_map(
        "Required Qualifications:\n"
        "- Python\n"
        "- SQL\n"
        "Preferred Qualifications:\n"
        "- AWS\n"
        "- Snowflake\n"
    )

    assert result["Python"] == "required"
    assert result["SQL"] == "required"
    assert result["AWS S3"] == "preferred"
    assert result["Snowflake"] == "preferred"


def test_required_overrides_preferred():
    result = as_map(
        "Preferred Skills:\n"
        "- Python\n"
        "Must Have:\n"
        "- Python\n"
    )

    assert result["Python"] == "required"


def test_unlabeled_requirements_remain_unspecified():
    result = as_map("Experience with Python and SQL.")

    assert result["Python"] == "unspecified"
    assert result["SQL"] == "unspecified"


def test_no_recognized_requirements():
    assert extract_requirements("Friendly and collaborative team.") == []


def test_empty_description():
    assert extract_requirements("") == []


def test_invalid_description():
    with pytest.raises(TypeError):
        extract_requirements(None)


def test_no_duplicate_skills():
    result = extract_requirements(
        "Required Qualifications:\n"
        "- SQL\n"
        "- SQL reconciliation\n"
    )

    assert sum(item["requirement"] == "SQL" for item in result) == 1
