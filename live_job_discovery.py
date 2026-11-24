"""Normalize and orchestrate live public ATS job discovery."""

from __future__ import annotations

import re
import html
from html.parser import HTMLParser

from live_job_connectors import (
    load_live_sources,
    get_enabled_boards,
    fetch_board,
    LiveSourceError,
)


INDIA_LOCATION_PATTERN = re.compile(
    r"\b(india|bengaluru|bangalore|hyderabad|pune|"
    r"mumbai|chennai|gurugram|gurgaon|noida|"
    r"delhi|kolkata|ahmedabad|kochi|"
    r"thiruvananthapuram|coimbatore)\b",
    re.IGNORECASE,
)

PREFERRED_CITIES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
}


class TextExtractor(HTMLParser):
    """Extract readable text from HTML descriptions."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

        if tag in {
            "p", "br", "div", "li", "h1",
            "h2", "h3", "h4", "tr"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

        if tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_text(value):
    if not isinstance(value, str):
        return ""

    return re.sub(r"\s+", " ", value).strip()


def clean_description(value):
    if not isinstance(value, str):
        return ""

    parser = TextExtractor()
    parser.feed(html.unescape(value))

    return "\n".join(
        line.strip()
        for line in "".join(parser.parts).splitlines()
        if line.strip()
    )


def infer_country(location):
    """Infer India only from recognizable location evidence."""

    if INDIA_LOCATION_PATTERN.search(location or ""):
        return "India"

    return ""


def normalize_location(location):
    location = clean_text(location)

    if not location:
        return ""

    matches = {
        city
        for alias, city in PREFERRED_CITIES.items()
        if re.search(
            rf"\b{re.escape(alias)}\b",
            location,
            re.IGNORECASE,
        )
    }

    if len(matches) == 1:
        city = next(iter(matches))

        # Do not collapse multi-location postings.
        if re.search(r"[;/|]|\bor\b", location, re.I):
            return location

        parts = [
            part.strip().casefold()
            for part in location.split(",")
        ]

        allowed = {
            "india", "in", "karnataka",
            "telangana", "maharashtra",
            "bangalore", "bengaluru",
            "hyderabad", "pune",
        }

        if all(part in allowed for part in parts):
            return city

    return location


def infer_work_mode(value="", is_remote=None):
    """Use explicit workplace evidence, not assumptions."""

    value = clean_text(value).casefold()
    value = re.sub(r"[-_\s]+", "", value)

    modes = {
        "remote": "Remote",
        "hybrid": "Hybrid",
        "onsite": "Onsite",
        "workfromhome": "Remote",
    }

    if value in modes:
        return modes[value]

    if is_remote is True:
        return "Remote"

    return ""


def normalize_posting(provider, raw, board):
    """Transform one ATS posting into a canonical record."""

    if provider == "greenhouse":

        title = raw.get("title")
        url = raw.get("absolute_url")

        location_data = raw.get("location") or {}

        location = (
            location_data.get("name", "")
            if isinstance(location_data, dict)
            else location_data
        )

        description = clean_description(
            raw.get("content")
        )

        mode = infer_work_mode(
            raw.get("workplaceType", "")
        )

    elif provider == "lever":

        categories = raw.get("categories") or {}

        if not isinstance(categories, dict):
            categories = {}

        title = raw.get("text")
        url = raw.get("hostedUrl")
        location = categories.get("location", "")

        description = (
            raw.get("descriptionPlain")
            or clean_description(
                raw.get("description")
            )
        )

        mode = infer_work_mode(
            raw.get("workplaceType", "")
        )

    elif provider == "ashby":

        title = raw.get("title")
        url = raw.get("jobUrl")
        location = raw.get("location", "")

        description = (
            raw.get("descriptionPlain")
            or clean_description(
                raw.get("descriptionHtml")
            )
        )

        mode = infer_work_mode(
            raw.get("workplaceType", ""),
            raw.get("isRemote"),
        )

    else:
        raise ValueError("Unsupported ATS provider")

    location = clean_text(location)

    return {
        "url": clean_text(url),
        "title": clean_text(title),
        "company": board["company"],
        "location": normalize_location(location),
        "country": infer_country(location),
        "work_mode": mode,
        "description": (
            description
            if isinstance(description, str)
            else ""
        ),
        "source_provider": provider,
        "source_board_id": board["board_id"],
        "source_job_id": str(
            raw.get("id") or url or ""
        ),
        "original_location": location,
    }


def discover_live_jobs(
    config=None,
    board_ids=None,
    fetcher=None,
):
    """Fetch and normalize enabled boards without saving jobs."""

    if config is None:
        config = load_live_sources()

    if fetcher is None:
        fetcher = fetch_board

    boards = get_enabled_boards(config)

    if board_ids is not None:
        selected = set(board_ids)

        boards = [
            board for board in boards
            if board["board_id"] in selected
        ]

    jobs = []
    source_results = []

    for board in boards:

        try:
            response = fetcher(
                board,
                config["settings"],
            )

            normalized = [
                normalize_posting(
                    board["provider"],
                    raw,
                    board,
                )
                for raw in response["jobs"]
            ]

            jobs.extend(normalized)

            source_results.append({
                "board_id": board["board_id"],
                "company": board["company"],
                "status": "success",
                "job_count": len(normalized),
                "error": "",
            })

        except (LiveSourceError, ValueError,
                TypeError, KeyError) as exc:

            source_results.append({
                "board_id": board["board_id"],
                "company": board["company"],
                "status": "failed",
                "job_count": 0,
                "error": str(exc),
            })

    india_jobs = [
        job for job in jobs
        if job["country"] == "India"
    ]

    return {
        "jobs": jobs,
        "india_jobs": india_jobs,
        "sources": source_results,
        "summary": {
            "sources_attempted": len(boards),
            "sources_successful": sum(
                source["status"] == "success"
                for source in source_results
            ),
            "sources_failed": sum(
                source["status"] == "failed"
                for source in source_results
            ),
            "total_jobs": len(jobs),
            "india_jobs": len(india_jobs),
            "unknown_country_jobs": sum(
                not job["country"]
                for job in jobs
            ),
            "india_missing_work_mode": sum(
                not job["work_mode"]
                for job in india_jobs
            ),
        },
    }
