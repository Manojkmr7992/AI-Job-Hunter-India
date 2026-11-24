"""Automated tests for BFSI employer reference data."""

import json
import pytest

from company_master import (
    load_company_master,
    get_companies,
    resolve_company,
    company_summary,
    normalize_company_name
)


def test_master_load():
    master = load_company_master()
    assert master["country"] == "India"
    assert master["version"] == "1.0"


def test_company_count():
    assert len(get_companies()) >= 122


def test_unique_company_ids():
    companies = get_companies()
    ids = [c["company_id"] for c in companies]
    assert len(ids) == len(set(ids))


def test_global_banks():
    assert len(get_companies(
        category="global_bank"
    )) >= 24


def test_high_priority_companies():
    assert len(get_companies(
        priority="high"
    )) >= 81


@pytest.mark.parametrize(
    "incoming,expected",
    [
        ("Citigroup", "Citi"),
        ("Citibank", "Citi"),
        ("CITI", "Citi"),
        ("JP Morgan", "JPMorgan Chase"),
        ("JPMC", "JPMorgan Chase"),
        ("Amex", "American Express"),
        ("BNY Mellon", "BNY"),
        ("LTI Mindtree", "LTIMindtree"),
        ("Tata Consultancy Services", "TCS"),
        ("SBI", "State Bank of India"),
        ("Barclays", "Barclays"),
        ("VISA", "Visa"),
        ("HDFC Bank", "HDFC Bank"),
        ("Deloitte", "Deloitte"),
        ("KPMG", "KPMG"),
        ("EY", "EY"),
        ("PWC", "PwC"),
        ("Wipro", "Wipro")
    ]
)
def test_company_resolution(incoming, expected):
    company = resolve_company(incoming)
    assert company is not None
    assert company["company_name"] == expected


def test_unknown_company_is_unclassified():
    assert resolve_company(
        "New Emerging BFSI Startup"
    ) is None


def test_empty_company_name():
    assert resolve_company("") is None


def test_normalization():
    assert normalize_company_name(
        "JP Morgan"
    ) == "jpmorgan"


def test_company_summary():
    summary = company_summary()

    assert summary["total_companies"] == sum(
        summary["categories"].values()
    )

    assert summary["total_companies"] == sum(
        summary["priorities"].values()
    )


def test_enabled_filter(tmp_path):
    master = load_company_master()
    master["companies"][0]["enabled"] = False

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    enabled = get_companies(
        enabled_only=True,
        path=path
    )

    assert len(enabled) == (
        len(master["companies"]) - 1
    )


def test_duplicate_company_id(tmp_path):
    master = load_company_master()

    master["companies"].append(
        master["companies"][0].copy()
    )

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    with pytest.raises(
        ValueError,
        match="Duplicate company ID"
    ):
        load_company_master(path)


def test_ambiguous_alias(tmp_path):
    master = load_company_master()

    master["companies"][1]["aliases"].append(
        master["companies"][0]["company_name"]
    )

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    with pytest.raises(
        ValueError,
        match="Ambiguous company alias"
    ):
        load_company_master(path)


def test_invalid_priority(tmp_path):
    master = load_company_master()
    master["companies"][0]["priority"] = "invalid"

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    with pytest.raises(
        ValueError,
        match="Invalid company priority"
    ):
        load_company_master(path)


def test_missing_required_field(tmp_path):
    master = load_company_master()
    del master["companies"][0]["company_id"]

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    with pytest.raises(
        ValueError,
        match="Missing fields"
    ):
        load_company_master(path)


def test_invalid_enabled_flag(tmp_path):
    master = load_company_master()
    master["companies"][0]["enabled"] = "yes"

    path = tmp_path / "companies.json"
    path.write_text(json.dumps(master))

    with pytest.raises(
        ValueError,
        match="Invalid enabled flag"
    ):
        load_company_master(path)
