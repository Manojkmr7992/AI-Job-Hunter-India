"""Configuration-driven job source registry."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "job_sources.json"

REQUIRED_FIELDS = {
    "source_id",
    "source_name",
    "category",
    "integration_method",
    "enabled",
    "configuration_status"
}


def load_registry(path=REGISTRY_PATH):
    """Load and validate the job source registry."""

    with Path(path).open(encoding="utf-8") as file:
        registry = json.load(file)

    if not isinstance(registry, dict):
        raise ValueError("Registry must be a JSON object")

    sources = registry.get("sources")

    if not isinstance(sources, list):
        raise ValueError("Sources must be a list")

    seen_ids = set()

    for source in sources:

        if not isinstance(source, dict):
            raise ValueError("Invalid source record")

        missing = REQUIRED_FIELDS - source.keys()

        if missing:
            raise ValueError(
                f"Missing required fields: {sorted(missing)}"
            )

        for field in REQUIRED_FIELDS - {"enabled"}:
            if not isinstance(source[field], str) or not source[field].strip():
                raise ValueError(f"Invalid field: {field}")

        source_id = source["source_id"]

        if source_id in seen_ids:
            raise ValueError(
                f"Duplicate source ID: {source_id}"
            )

        if not isinstance(source["enabled"], bool):
            raise ValueError(
                f"Invalid enabled flag: {source_id}"
            )

        seen_ids.add(source_id)

    return registry


def get_sources(
    category=None,
    integration_method=None,
    enabled_only=False,
    path=REGISTRY_PATH
):
    """Retrieve sources using optional filters."""

    sources = load_registry(path)["sources"]

    if category is not None:
        sources = [
            s for s in sources
            if s["category"] == category
        ]

    if integration_method is not None:
        sources = [
            s for s in sources
            if s["integration_method"] == integration_method
        ]

    if enabled_only:
        sources = [
            s for s in sources
            if s["enabled"]
        ]

    return sources


def get_source(source_id, path=REGISTRY_PATH):
    """Retrieve a single source by its unique ID."""

    for source in get_sources(path=path):
        if source["source_id"] == source_id:
            return source

    raise KeyError(f"Unknown source: {source_id}")


def registry_summary(path=REGISTRY_PATH):
    """Return source registry statistics."""

    registry = load_registry(path)
    sources = registry["sources"]

    return {
        "version": registry["version"],
        "country": registry["country"],
        "total_sources": len(sources),
        "enabled_sources": sum(
            s["enabled"] for s in sources
        ),
        "disabled_sources": sum(
            not s["enabled"] for s in sources
        )
    }
