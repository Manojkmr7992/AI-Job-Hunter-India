"""Automated tests for job classification."""

import json
import pytest

from job_classifier import (
    load_taxonomy,
    contains_phrase,
    classify_role,
    classify_seniority,
    classify_bfsi,
    classify_skills,
    classify_employer,
    classify_location,
    classify_job
)


def test_taxonomy_load():
    taxonomy = load_taxonomy()

    assert taxonomy["country"] == "India"
    assert len(taxonomy["role_families"]) == 9
    assert len(taxonomy["bfsi_domains"]) == 16
    assert sum(taxonomy["ranking_weights"].values()) == 100


def test_open_employer_policy():
    policy = load_taxonomy()["search_policy"]

    assert policy["restrict_to_company_master"] is False
    assert policy["allow_unknown_employers"] is True


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Senior Technical Product Owner", "product_ownership"),
        ("Technical Product Manager", "product_management"),
        ("Lead Business Systems Analyst", "business_systems_analysis"),
        ("Senior Business Analyst", "business_analysis"),
        ("Data Product Manager", "data_products"),
        ("GenAI Product Manager", "ai_products"),
        ("Technology Product Management Senior Lead Analyst",
         "banking_leadership"),
        ("Director of Product Management", "product_strategy"),
        ("Senior Product Analyst", "product_analysis")
    ]
)
def test_role_classification(title, expected):
    assert classify_role(title)["primary_role"] == expected


def test_unknown_role():
    result = classify_role("Senior Tax Consultant")

    assert result["primary_role"] is None
    assert result["role_status"] == "review"


@pytest.mark.parametrize(
    "title,description,expected",
    [
        ("Senior Product Owner", "", "preferred"),
        ("Lead Business Systems Analyst", "", "preferred"),
        ("Principal Product Manager", "", "preferred"),
        ("VP Product Owner", "", "preferred"),
        ("Junior Business Analyst", "", "lower_priority"),
        ("Product Manager", "", "review"),
        ("Technical Product Manager",
         "10 years of experience", "preferred"),
        ("Product Owner",
         "8+ years of relevant experience", "preferred"),
        ("Product Owner",
         "3 years of experience", "review")
    ]
)
def test_seniority(title, description, expected):
    result = classify_seniority(title, description)

    assert result["seniority"] == expected


@pytest.mark.parametrize(
    "description,expected",
    [
        ("AML transaction monitoring", "aml_transaction_monitoring"),
        ("Credit cards and card processing", "credit_debit_cards"),
        ("Digital payments and UPI", "payments"),
        ("HELOC and mortgage servicing", "mortgage_heloc"),
        ("Credit risk and FICO", "credit_risk"),
        ("KYC and sanctions screening", "kyc_sanctions"),
        ("Digital banking and open banking", "core_digital_banking"),
        ("Fraud detection", "fraud_detection"),
        ("Banking data engineering", "bfsi_data_cloud_ai")
    ]
)
def test_bfsi_domains(description, expected):
    result = classify_bfsi("Product Owner", description)

    assert expected in result["bfsi_domains"]


def test_multiple_bfsi_domains():
    result = classify_bfsi(
        "Product Owner",
        "AML transaction monitoring, credit cards and payments"
    )

    assert "aml_transaction_monitoring" in result["bfsi_domains"]
    assert "credit_debit_cards" in result["bfsi_domains"]
    assert "payments" in result["bfsi_domains"]


def test_unconfirmed_bfsi():
    result = classify_bfsi(
        "Product Owner",
        "Retail clothing inventory"
    )

    assert result["bfsi_status"] == "review"


def test_skill_classification():
    result = classify_skills(
        "Technical Product Owner",
        "SQL, Snowflake, AWS, product roadmap, UAT and machine learning"
    )

    assert len(result["skill_categories"]) == 5


def test_whole_word_matching():
    assert contains_phrase("AML transaction monitoring", "AML")
    assert not contains_phrase("HTML development", "AML")
    assert not contains_phrase("Chair design", "AI")
    assert not contains_phrase("PostgreSQL", "SQL")


def test_known_employer():
    result = classify_employer("Citigroup")

    assert result["known_employer"] is True
    assert result["canonical_company"] == "Citi"


def test_unknown_employer():
    result = classify_employer("New BFSI Startup")

    assert result["known_employer"] is False
    assert result["company_category"] == "unclassified"


@pytest.mark.parametrize(
    "location,country,work_mode,expected",
    [
        ("Bengaluru", "India", "hybrid", "preferred"),
        ("Bangalore", "India", "onsite", "preferred"),
        ("Hyderabad", "India", "hybrid", "preferred"),
        ("Pune", "India", "onsite", "preferred"),
        ("Remote", "India", "remote", "preferred"),
        ("Mumbai", "India", "onsite", "outside_preferred_cities"),
        ("London", "United Kingdom", "hybrid", "outside_target"),
        ("Remote", "", "remote", "review"),
        ("", "", "", "review")
    ]
)
def test_location(location, country, work_mode, expected):
    result = classify_location({
        "location": location,
        "country": country,
        "work_mode": work_mode
    })

    assert result["location_status"] == expected


def test_unknown_employer_relevant_job():
    result = classify_job({
        "title": "Senior Technical Product Owner",
        "company": "Unregistered FinTech",
        "location": "Hyderabad",
        "country": "India",
        "description": "AML transaction monitoring and AWS"
    })

    assert result["known_employer"] is False
    assert result["classification_status"] == "relevant"


def test_empty_job_retained_for_review():
    result = classify_job({})

    assert result["classification_status"] == "review"


def test_invalid_weights(tmp_path):
    taxonomy = load_taxonomy()
    taxonomy["ranking_weights"]["location"] = 10

    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(taxonomy))

    with pytest.raises(ValueError, match="must total 100"):
        load_taxonomy(path)


def test_company_whitelist_rejected(tmp_path):
    taxonomy = load_taxonomy()
    taxonomy["search_policy"]["restrict_to_company_master"] = True

    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(taxonomy))

    with pytest.raises(ValueError, match="whitelist"):
        load_taxonomy(path)


def test_missing_taxonomy_section(tmp_path):
    taxonomy = load_taxonomy()
    del taxonomy["bfsi_domains"]

    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(taxonomy))

    with pytest.raises(ValueError, match="Missing taxonomy"):
        load_taxonomy(path)
