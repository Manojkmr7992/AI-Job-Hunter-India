"""Offline regression tests for live ATS connectors."""

import pytest

from live_job_connectors import (
    load_live_sources,
    get_enabled_boards,
    build_api_url,
    extract_postings,
    LiveSourceError,
)

from live_job_discovery import (
    infer_country,
    normalize_location,
    infer_work_mode,
    clean_description,
    normalize_posting,
    discover_live_jobs,
)


def test_source_configuration():
    config = load_live_sources()

    assert config["settings"]["verify_ssl"] is True
    assert config["settings"]["auto_import"] is False
    assert config["boards"]

    ids = [
        board["board_id"]
        for board in config["boards"]
    ]

    assert len(ids) == len(set(ids))


def test_enabled_boards():
    config = load_live_sources()
    boards = get_enabled_boards(config)

    assert boards
    assert all(board["enabled"] for board in boards)


@pytest.mark.parametrize(
    "provider,token,expected",
    [
        (
            "greenhouse",
            "demo",
            "https://boards-api.greenhouse.io/v1/boards/"
            "demo/jobs?content=true",
        ),
        (
            "lever",
            "demo",
            "https://api.lever.co/v0/postings/demo?mode=json",
        ),
        (
            "ashby",
            "demo",
            "https://api.ashbyhq.com/posting-api/job-board/demo",
        ),
    ],
)
def test_api_url_construction(provider, token, expected):
    assert build_api_url(provider, token) == expected


def test_unsupported_provider():
    with pytest.raises(ValueError):
        build_api_url("unsupported", "demo")


@pytest.mark.parametrize(
    "token",
    ["../demo", "demo/path", "demo?query=1"],
)
def test_invalid_board_token(token):
    with pytest.raises(ValueError):
        build_api_url("greenhouse", token)


@pytest.mark.parametrize(
    "provider,payload",
    [
        ("greenhouse", {"jobs": [{"id": 1}]}),
        ("lever", [{"id": 1}]),
        ("ashby", {"jobs": [{"id": 1}]}),
    ],
)
def test_valid_provider_response(provider, payload):
    assert extract_postings(provider, payload) == [{"id": 1}]


@pytest.mark.parametrize(
    "provider,payload",
    [
        ("greenhouse", {"invalid": []}),
        ("lever", {"jobs": []}),
        ("ashby", {"jobs": "invalid"}),
        ("greenhouse", {"jobs": ["invalid"]}),
    ],
)
def test_invalid_provider_response(provider, payload):
    with pytest.raises(LiveSourceError):
        extract_postings(provider, payload)


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Bengaluru, India", "India"),
        ("Hyderabad", "India"),
        ("Pune, Maharashtra", "India"),
        ("London, United Kingdom", ""),
        ("New York, USA", ""),
        ("", ""),
    ],
)
def test_country_inference(location, expected):
    assert infer_country(location) == expected


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Bangalore, India", "Bengaluru"),
        ("Hyderabad, India", "Hyderabad"),
        ("Pune, India", "Pune"),
    ],
)
def test_location_normalization(location, expected):
    assert normalize_location(location) == expected


@pytest.mark.parametrize(
    "value,is_remote,expected",
    [
        ("hybrid", None, "Hybrid"),
        ("on-site", None, "Onsite"),
        ("remote", None, "Remote"),
        ("", True, "Remote"),
        ("", False, ""),
        ("", None, ""),
    ],
)
def test_work_mode_inference(value, is_remote, expected):
    assert infer_work_mode(value, is_remote) == expected


def test_description_cleaning():
    result = clean_description(
        "<p>Product Owner</p>"
        "<script>hidden content</script>"
        "<p>Banking and payments</p>"
    )

    assert "Product Owner" in result
    assert "Banking and payments" in result
    assert "hidden content" not in result


def make_board(provider):
    return {
        "board_id": f"{provider}_demo",
        "company": "Demo Bank",
        "provider": provider,
        "board_token": "demo",
        "api_url": build_api_url(provider, "demo"),
        "enabled": True,
    }


@pytest.mark.parametrize(
    "provider,raw",
    [
        (
            "greenhouse",
            {
                "id": 1,
                "title": "Senior Product Owner",
                "absolute_url": "https://example.com/jobs/1",
                "location": {"name": "Hyderabad, India"},
                "content": "<p>Banking products</p>",
                "workplaceType": "hybrid",
            },
        ),
        (
            "lever",
            {
                "id": "2",
                "text": "Senior Product Owner",
                "hostedUrl": "https://example.com/jobs/2",
                "categories": {
                    "location": "Hyderabad, India",
                },
                "descriptionPlain": "Banking products",
                "workplaceType": "hybrid",
            },
        ),
        (
            "ashby",
            {
                "id": "3",
                "title": "Senior Product Owner",
                "jobUrl": "https://example.com/jobs/3",
                "location": "Hyderabad, India",
                "descriptionPlain": "Banking products",
                "workplaceType": "Hybrid",
            },
        ),
    ],
)
def test_provider_normalization(provider, raw):
    job = normalize_posting(
        provider,
        raw,
        make_board(provider),
    )

    assert job["title"] == "Senior Product Owner"
    assert job["company"] == "Demo Bank"
    assert job["country"] == "India"
    assert job["location"] == "Hyderabad"
    assert job["work_mode"] == "Hybrid"
    assert job["source_provider"] == provider
    assert job["source_job_id"]
    assert job["url"].startswith("https://")


def test_partial_source_failure():
    config = {
        "boards": [
            make_board("greenhouse"),
            make_board("lever"),
        ],
        "settings": {
            "verify_ssl": True,
            "auto_import": False,
        },
    }

    def fake_fetcher(board, settings):
        if board["provider"] == "lever":
            raise LiveSourceError("Simulated source failure")

        return {
            "board_id": board["board_id"],
            "company": board["company"],
            "provider": board["provider"],
            "job_count": 1,
            "jobs": [
                {
                    "id": 1,
                    "title": "Senior Product Owner",
                    "absolute_url": "https://example.com/jobs/1",
                    "location": {
                        "name": "Hyderabad, India",
                    },
                    "content": "<p>Banking products</p>",
                }
            ],
        }

    report = discover_live_jobs(
        config=config,
        fetcher=fake_fetcher,
    )

    assert report["summary"]["sources_attempted"] == 2
    assert report["summary"]["sources_successful"] == 1
    assert report["summary"]["sources_failed"] == 1
    assert report["summary"]["total_jobs"] == 1
    assert report["summary"]["india_jobs"] == 1


def test_disabled_sources_not_called():
    board = make_board("greenhouse")
    board["enabled"] = False

    config = {
        "boards": [board],
        "settings": {
            "verify_ssl": True,
            "auto_import": False,
        },
    }

    def unexpected_fetcher(board, settings):
        pytest.fail("Disabled source was called")

    report = discover_live_jobs(
        config=config,
        fetcher=unexpected_fetcher,
    )

    assert report["summary"]["sources_attempted"] == 0
    assert report["jobs"] == []
