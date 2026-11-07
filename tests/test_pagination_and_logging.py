
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraper import (
    ScrapingAccessError,
    create_scraping_run,
    extract_next_page_url,
    scrape_truelancer_pages,
    update_scraping_run,
    validate_pagination_url,
)


START_URL = "https://www.truelancer.com/projects?page=1"
SECOND_PAGE_URL = "https://www.truelancer.com/projects?page=2"


def make_page(
    title: str,
    next_url: str | None = None,
) -> str:
    """Build local HTML containing Truelancer-style embedded JSON."""
    project = {
        "title": title,
        "description": "Create a project for testing.",
        "budget": "500",
        "currency": "USD",
        "created_at": "2026-11-01",
        "skills": [
            {"tagName": "Python"},
        ],
        "link": (
            "https://www.truelancer.com/"
            f"freelance-project/{title.lower().replace(' ', '-')}-123"
        ),
        "jobTypeName": "Fixed Price",
    }

    payload = {
        "props": {
            "pageProps": {
                "data": {
                    "projects": {
                        "data": [project],
                        "next_page_url": next_url,
                    }
                }
            }
        }
    }

    return (
        '<html><body>'
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script>"
        "</body></html>"
    )


# ============================================================
# NEXT-PAGE URL EXTRACTION
# ============================================================

def test_extracts_next_page_url():
    html = make_page(
        "First project",
        next_url=SECOND_PAGE_URL,
    )

    result = extract_next_page_url(html)

    assert result == SECOND_PAGE_URL


def test_returns_none_when_no_next_page_exists():
    html = make_page("First project")

    result = extract_next_page_url(html)

    assert result is None


def test_returns_none_when_embedded_data_is_missing():
    html = "<html><body>No embedded data</body></html>"

    result = extract_next_page_url(html)

    assert result is None


def test_returns_none_for_invalid_embedded_json():
    html = """
    <html>
        <script id="__NEXT_DATA__">
            invalid json
        </script>
    </html>
    """

    result = extract_next_page_url(html)

    assert result is None


# ============================================================
# PAGINATION URL VALIDATION
# ============================================================

def test_accepts_same_truelancer_host():
    assert validate_pagination_url(
        SECOND_PAGE_URL,
        START_URL,
    )


def test_rejects_different_host():
    malicious_url = "https://example.com/page=2"

    assert not validate_pagination_url(
        malicious_url,
        START_URL,
    )


def test_rejects_http_pagination_url():
    insecure_url = "http://www.truelancer.com/projects?page=2"

    assert not validate_pagination_url(
        insecure_url,
        START_URL,
    )


def test_rejects_different_truelancer_subdomain():
    different_host = "https://api.truelancer.com/projects?page=2"

    assert not validate_pagination_url(
        different_host,
        START_URL,
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@www.truelancer.com/projects?page=2",
        "https://www.truelancer.com:8443/projects?page=2",
        "https://www.truelancer.com:abc/projects?page=2",
    ],
)
def test_rejects_credentials_or_unexpected_ports(url):
    assert not validate_pagination_url(
        url,
        START_URL,
    )


def test_rejects_credentials_or_unexpected_port_in_start_url():
    unsafe_start_urls = [
        "https://user:pass@www.truelancer.com/projects?page=1",
        "https://www.truelancer.com:8443/projects?page=1",
    ]

    for unsafe_url in unsafe_start_urls:
        assert not validate_pagination_url(
            SECOND_PAGE_URL,
            unsafe_url,
        )


# ============================================================
# MULTI-PAGE SCRAPING
# ============================================================

def test_scrapes_multiple_pages():
    first_page = make_page(
        "First project",
        next_url=SECOND_PAGE_URL,
    )

    second_page = make_page(
        "Second project",
    )

    fetcher = Mock(
        side_effect=[
            first_page,
            second_page,
        ]
    )

    sleep_function = Mock()

    projects = scrape_truelancer_pages(
        start_url=START_URL,
        max_pages=3,
        min_request_interval=1,
        fetcher=fetcher,
        sleep_fn=sleep_function,
    )

    assert len(projects) == 2

    assert projects[0].title == "First project"
    assert projects[1].title == "Second project"

    assert fetcher.call_count == 2
    assert sleep_function.call_count == 1

    fetcher.assert_any_call(START_URL)
    fetcher.assert_any_call(SECOND_PAGE_URL)


def test_respects_maximum_page_limit():
    first_page = make_page(
        "First project",
        next_url=SECOND_PAGE_URL,
    )

    fetcher = Mock(return_value=first_page)

    projects = scrape_truelancer_pages(
        start_url=START_URL,
        max_pages=1,
        min_request_interval=0,
        fetcher=fetcher,
        sleep_fn=Mock(),
    )

    assert len(projects) == 1
    assert fetcher.call_count == 1


def test_does_not_sleep_before_first_page():
    first_page = make_page("First project")

    fetcher = Mock(return_value=first_page)
    sleep_function = Mock()

    scrape_truelancer_pages(
        start_url=START_URL,
        max_pages=1,
        min_request_interval=1,
        fetcher=fetcher,
        sleep_fn=sleep_function,
    )

    sleep_function.assert_not_called()


def test_rejects_invalid_start_url():
    with pytest.raises(ValueError):
        scrape_truelancer_pages(
            start_url="https://example.com/projects",
            fetcher=Mock(),
            sleep_fn=Mock(),
        )


@pytest.mark.parametrize(
    "start_url",
    [
        "https://user:pass@www.truelancer.com/projects?page=1",
        "https://www.truelancer.com:8443/projects?page=1",
        "https://www.truelancer.com:abc/projects?page=1",
    ],
)
def test_rejects_unsafe_start_url(start_url):
    with pytest.raises(ValueError):
        scrape_truelancer_pages(
            start_url=start_url,
            fetcher=Mock(),
            sleep_fn=Mock(),
        )


def test_rejects_zero_max_pages():
    with pytest.raises(ValueError):
        scrape_truelancer_pages(
            start_url=START_URL,
            max_pages=0,
            fetcher=Mock(),
            sleep_fn=Mock(),
        )


def test_rejects_negative_request_interval():
    with pytest.raises(ValueError):
        scrape_truelancer_pages(
            start_url=START_URL,
            min_request_interval=-1,
            fetcher=Mock(),
            sleep_fn=Mock(),
        )


def test_stops_when_next_page_host_is_invalid():
    first_page = make_page(
        "First project",
        next_url="https://example.com/malicious-page",
    )

    fetcher = Mock(return_value=first_page)

    with pytest.raises(ScrapingAccessError):
        scrape_truelancer_pages(
            start_url=START_URL,
            max_pages=3,
            min_request_interval=0,
            fetcher=fetcher,
            sleep_fn=Mock(),
        )

    assert fetcher.call_count == 1


# ============================================================
# SCRAPING-RUN API LOGGING
# ============================================================

def test_create_scraping_run():
    mock_response = Mock()
    mock_response.json.return_value = {
        "id": "test-run-id",
    }

    with patch(
        "src.scraper.requests.post",
        return_value=mock_response,
    ) as mock_post:

        run_id = create_scraping_run(
            source_id="test-source-id",
            api_endpoint="http://localhost:8000/scraping-runs",
        )

    assert run_id == "test-run-id"

    mock_post.assert_called_once_with(
        "http://localhost:8000/scraping-runs",
        json={
            "source_id": "test-source-id",
            "status": "RUNNING",
        },
        timeout=15,
    )

    mock_response.raise_for_status.assert_called_once()


def test_create_scraping_run_rejects_missing_id():
    mock_response = Mock()
    mock_response.json.return_value = {}

    with patch(
        "src.scraper.requests.post",
        return_value=mock_response,
    ):
        with pytest.raises(ValueError):
            create_scraping_run(
                source_id="test-source-id",
            )


def test_update_scraping_run_success():
    mock_response = Mock()

    with patch(
        "src.scraper.requests.patch",
        return_value=mock_response,
    ) as mock_patch:

        update_scraping_run(
            run_id="test-run-id",
            status="SUCCESS",
            records_found=15,
            api_endpoint="http://localhost:8000/scraping-runs",
        )

    mock_patch.assert_called_once_with(
        "http://localhost:8000/scraping-runs/test-run-id",
        json={
            "status": "SUCCESS",
            "records_found": 15,
            "error_log": None,
        },
        timeout=15,
    )

    mock_response.raise_for_status.assert_called_once()


def test_update_scraping_run_failed_status():
    mock_response = Mock()

    with patch(
        "src.scraper.requests.patch",
        return_value=mock_response,
    ) as mock_patch:

        update_scraping_run(
            run_id="test-run-id",
            status="FAILED",
            records_found=0,
            error_log="Test error",
        )

    payload = mock_patch.call_args.kwargs["json"]

    assert payload["status"] == "FAILED"
    assert payload["records_found"] == 0
    assert payload["error_log"] == "Test error"


def test_update_scraping_run_rejects_invalid_status():
    with pytest.raises(ValueError):
        update_scraping_run(
            run_id="test-run-id",
            status="RUNNING",
            records_found=0,
        )


def test_update_scraping_run_rejects_negative_record_count():
    with pytest.raises(ValueError):
        update_scraping_run(
            run_id="test-run-id",
            status="SUCCESS",
            records_found=-1,
        )


def test_update_scraping_run_propagates_api_error():
    with patch(
        "src.scraper.requests.patch",
        side_effect=requests.Timeout,
    ):
        with pytest.raises(requests.Timeout):
            update_scraping_run(
                run_id="test-run-id",
                status="SUCCESS",
                records_found=10,
            )
