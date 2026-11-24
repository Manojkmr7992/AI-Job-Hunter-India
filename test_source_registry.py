"""Automated tests for the job source registry."""

import json
import pytest

from source_registry import (
    load_registry,
    get_sources,
    get_source,
    registry_summary
)


def test_registry_load():
    registry = load_registry()
    assert registry["country"] == "India"
    assert registry["version"] == "1.0"


def test_registered_source_count():
    assert len(get_sources()) == 18


def test_unique_source_ids():
    sources = get_sources()
    ids = [s["source_id"] for s in sources]
    assert len(ids) == len(set(ids))


def test_gmail_alert_sources():
    sources = get_sources(
        integration_method="gmail_alert"
    )
    assert len(sources) == 8


def test_recruiter_email_source():
    source = get_source("recruiter_email")
    assert source["integration_method"] == "gmail_api"


def test_ats_sources():
    sources = get_sources(category="ats")
    assert len(sources) == 4


def test_unknown_source():
    with pytest.raises(KeyError):
        get_source("unknown_portal")


def test_registry_summary():
    summary = registry_summary()
    assert summary["total_sources"] == 18
    assert (
        summary["enabled_sources"]
        + summary["disabled_sources"]
        == summary["total_sources"]
    )


def test_enabled_source_filter(tmp_path):
    registry = load_registry()

    for source in registry["sources"]:
        source["enabled"] = False

    registry["sources"][0]["enabled"] = True

    path = tmp_path / "sources.json"
    path.write_text(json.dumps(registry))

    enabled = get_sources(
        enabled_only=True,
        path=path
    )

    assert len(enabled) == 1
    assert enabled[0]["source_id"] == "naukri"


def test_duplicate_source_rejected(tmp_path):
    registry = load_registry()
    registry["sources"].append(
        registry["sources"][0].copy()
    )

    path = tmp_path / "sources.json"
    path.write_text(json.dumps(registry))

    with pytest.raises(ValueError, match="Duplicate"):
        load_registry(path)


def test_missing_required_field(tmp_path):
    registry = load_registry()
    del registry["sources"][0]["source_id"]

    path = tmp_path / "sources.json"
    path.write_text(json.dumps(registry))

    with pytest.raises(ValueError, match="Missing"):
        load_registry(path)


def test_invalid_enabled_flag(tmp_path):
    registry = load_registry()
    registry["sources"][0]["enabled"] = "yes"

    path = tmp_path / "sources.json"
    path.write_text(json.dumps(registry))

    with pytest.raises(ValueError, match="Invalid enabled"):
        load_registry(path)


def test_invalid_json(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text("invalid json")

    with pytest.raises(json.JSONDecodeError):
        load_registry(path)
