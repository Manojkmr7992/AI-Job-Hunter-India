"""Secure, configuration-driven public ATS connectors."""

from __future__ import annotations

import json
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


CONFIG_PATH = Path(__file__).resolve().parent / "live_job_sources.json"

SUPPORTED_PROVIDERS = {
    "greenhouse",
    "lever",
    "ashby",
}

RETRYABLE_HTTP_CODES = {
    429, 500, 502, 503, 504
}


class LiveSourceError(Exception):
    """Raised when a live job source cannot be retrieved."""


def load_live_sources(path=CONFIG_PATH):
    """Load and validate employer board configuration."""

    with Path(path).open(encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid source configuration")

    settings = config.get("settings", {})
    boards = config.get("boards")

    if not isinstance(boards, list):
        raise ValueError("Boards must be a list")

    if settings.get("verify_ssl") is not True:
        raise ValueError("SSL verification must be enabled")

    if settings.get("auto_import") is not False:
        raise ValueError("Automatic import is not permitted")

    seen = set()

    required = {
        "board_id",
        "company",
        "provider",
        "board_token",
        "api_url",
        "enabled",
    }

    for board in boards:

        if not isinstance(board, dict):
            raise ValueError("Invalid board configuration")

        if not required.issubset(board):
            raise ValueError("Missing required board fields")

        if board["board_id"] in seen:
            raise ValueError("Duplicate board ID")

        seen.add(board["board_id"])

        if board["provider"] not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported ATS provider")

        if not isinstance(board["enabled"], bool):
            raise ValueError("Enabled must be a boolean")

        expected_url = build_api_url(
            board["provider"],
            board["board_token"],
        )

        if board["api_url"] != expected_url:
            raise ValueError("Invalid board API URL")

    return config


def build_api_url(provider, token):
    """Construct an endpoint using approved ATS hosts."""

    import re

    if not isinstance(token, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", token
    ):
        raise ValueError("Invalid board token")

    templates = {
        "greenhouse": (
            "https://boards-api.greenhouse.io"
            "/v1/boards/{token}/jobs?content=true"
        ),
        "lever": (
            "https://api.lever.co/v0/postings/"
            "{token}?mode=json"
        ),
        "ashby": (
            "https://api.ashbyhq.com"
            "/posting-api/job-board/{token}"
        ),
    }

    if provider not in templates:
        raise ValueError("Unsupported ATS provider")

    return templates[provider].format(token=token)


def get_enabled_boards(config=None):
    """Return only enabled employer boards."""

    if config is None:
        config = load_live_sources()

    return [
        board
        for board in config["boards"]
        if board["enabled"]
    ]


def extract_postings(provider, payload):
    """Extract raw postings from provider JSON."""

    if provider == "lever":
        jobs = payload

    elif provider in {"greenhouse", "ashby"}:
        if not isinstance(payload, dict):
            raise LiveSourceError("Expected JSON object")

        jobs = payload.get("jobs")

    else:
        raise ValueError("Unsupported ATS provider")

    if not isinstance(jobs, list):
        raise LiveSourceError("Expected job posting list")

    if any(not isinstance(job, dict) for job in jobs):
        raise LiveSourceError("Invalid job posting record")

    return jobs


def fetch_board(board, settings):
    """Fetch raw postings without database writes."""

    if not board["enabled"]:
        raise LiveSourceError("Employer board is disabled")

    if settings.get("verify_ssl") is not True:
        raise ValueError("SSL verification is required")

    provider = board["provider"]

    url = build_api_url(
        provider,
        board["board_token"],
    )

    if board["api_url"] != url:
        raise ValueError("Invalid board API URL")

    timeout = settings.get(
        "request_timeout_seconds", 20
    )

    retries = settings.get("max_retries", 2)

    backoff = settings.get(
        "retry_backoff_seconds", 2
    )

    if not isinstance(retries, int) or not 0 <= retries <= 3:
        raise ValueError("Invalid retry configuration")

    if not 0 < timeout <= 60:
        raise ValueError("Invalid timeout")

    if not 0 <= backoff <= 10:
        raise ValueError("Invalid retry backoff")

    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "AI-Job-Hunter-India/1.0",
        },
    )

    for attempt in range(retries + 1):

        try:
            with urlopen(
                request,
                timeout=timeout,
                context=context,
            ) as response:

                raw = response.read(25 * 1024 * 1024 + 1)

                if len(raw) > 25 * 1024 * 1024:
                    raise LiveSourceError(
                        "API response exceeds size limit"
                    )

                payload = json.loads(raw)

            postings = extract_postings(
                provider,
                payload,
            )

            return {
                "board_id": board["board_id"],
                "company": board["company"],
                "provider": provider,
                "job_count": len(postings),
                "jobs": postings,
            }

        except HTTPError as exc:

            if (
                exc.code not in RETRYABLE_HTTP_CODES
                or attempt == retries
            ):
                raise LiveSourceError(
                    f"HTTP {exc.code}: {board['board_id']}"
                ) from exc

            retry_after = exc.headers.get("Retry-After", "")

            if retry_after.isdigit():
                delay = int(retry_after)

                if delay > 60:
                    raise LiveSourceError(
                        "Source requested extended retry delay"
                    ) from exc
            elif retry_after:
                raise LiveSourceError(
                    "Source requested deferred retry"
                ) from exc
            else:
                delay = backoff * (2 ** attempt)

            time.sleep(delay)
            continue

        except (URLError, TimeoutError) as exc:

            if isinstance(
                getattr(exc, "reason", None),
                ssl.SSLCertVerificationError,
            ):
                raise LiveSourceError(
                    "SSL certificate verification failed"
                ) from exc

            if attempt == retries:
                raise LiveSourceError(
                    f"Connection failed: {board['board_id']}"
                ) from exc

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LiveSourceError(
                "Invalid JSON response"
            ) from exc

        time.sleep(backoff * (2 ** attempt))

    raise LiveSourceError("Request attempts exhausted")
