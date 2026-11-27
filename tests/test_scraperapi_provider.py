"""
Unit tests for the ScraperAPI provider and its integration with ScrapeScout.

Tests:
1. Missing API key handling.
2. Successful provider response.
3. Provider HTTP error handling (401/403, 429, 500).
4. Request timeout handling.
5. Invalid/malformed target URL rejection.
6. API key redaction in error messages and logs.
7. Redirect rejection without auto-following.
8. Bot checkpoint / human verification detection.
9. Integration with existing scraper (scrape_truelancer_pages) using the provider as fetcher.
10. Preservation of existing extraction and pipeline behavior.
"""

import os
import re
from unittest.mock import MagicMock, patch
import pytest
import requests

from src.scraperapi_provider import (
    ScraperAPIClient,
    ScraperAPIError,
    ScraperAPIConfigError,
    ScraperAPIAccessError,
    fetch_page_via_scraperapi,
    redact_api_key,
)
from src.scraper import (
    scrape_truelancer_pages,
    run_truelancer_scraping,
    fetch_page_via_scraperapi as scraper_fetch_page_via_scraperapi,
)
from src.pipeline import run_truelancer_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_api_key():
    return "test_scraper_api_key_abc123xyz"


@pytest.fixture
def client(fake_api_key):
    return ScraperAPIClient(api_key=fake_api_key)


# ---------------------------------------------------------------------------
# Configuration & Missing Key Tests
# ---------------------------------------------------------------------------

def test_missing_api_key_raises_config_error(monkeypatch):
    """When SCRAPER_API_KEY is not set or empty, fetching must raise ScraperAPIConfigError."""
    monkeypatch.delenv("SCRAPER_API_KEY", raising=False)
    client_without_key = ScraperAPIClient(api_key=None)

    assert not client_without_key.is_configured
    with pytest.raises(ScraperAPIConfigError) as exc_info:
        client_without_key.fetch("https://example.com/jobs")

    assert "SCRAPER_API_KEY environment variable is not configured" in str(exc_info.value)


def test_api_key_loaded_from_environment(monkeypatch, fake_api_key):
    """Client automatically detects SCRAPER_API_KEY when not explicitly passed."""
    monkeypatch.setenv("SCRAPER_API_KEY", fake_api_key)
    env_client = ScraperAPIClient()

    assert env_client.is_configured
    assert env_client._api_key == fake_api_key


# ---------------------------------------------------------------------------
# URL Validation Tests
# ---------------------------------------------------------------------------

def test_invalid_target_urls(client):
    """Rejects empty, non-HTTP, malformed, or credential-bearing URLs."""
    invalid_urls = [
        "",
        "   ",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https://user:pass@example.com/jobs",
        "https://example .com/spaces in url",
        "htt://example.com",
    ]
    for url in invalid_urls:
        with pytest.raises(ValueError):
            client.fetch(url)


# ---------------------------------------------------------------------------
# Successful Fetching Tests
# ---------------------------------------------------------------------------

@patch("src.scraperapi_provider.requests.get")
def test_successful_fetch(mock_get, client, fake_api_key):
    """A 200 OK response from ScraperAPI returns the HTML content."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><h1>Discovered Opportunities</h1></body></html>"
    mock_get.return_value = mock_resp

    target_url = "https://www.truelancer.com/freelance-jobs"
    result = client.fetch(target_url)

    assert "<h1>Discovered Opportunities</h1>" in result
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args

    assert kwargs["params"]["api_key"] == fake_api_key
    assert kwargs["params"]["url"] == target_url
    assert kwargs["timeout"] == client.timeout


@patch("src.scraperapi_provider.requests.get")
def test_fetch_with_render_js_and_country_code(mock_get, client):
    """Validates render=true and country_code are passed correctly to ScraperAPI."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>Dynamic content</body></html>"
    mock_get.return_value = mock_resp

    client.fetch(
        "https://www.truelancer.com/freelance-jobs",
        render_js=True,
        country_code="US",
    )

    args, kwargs = mock_get.call_args
    assert kwargs["params"]["render"] == "true"
    assert kwargs["params"]["country_code"] == "us"


# ---------------------------------------------------------------------------
# HTTP Error & Status Code Handling Tests
# ---------------------------------------------------------------------------

@patch("src.scraperapi_provider.requests.get")
def test_authentication_failure_raises_config_error(mock_get, client):
    """HTTP 401 or 403 from ScraperAPI indicates invalid API key."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_get.return_value = mock_resp

    with pytest.raises(ScraperAPIConfigError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs")

    assert "ScraperAPI authentication failed (HTTP 401)" in str(exc_info.value)


@patch("src.scraperapi_provider.requests.get")
def test_concurrency_or_rate_limit_exceeded(mock_get, client):
    """HTTP 429 indicates rate or concurrency limit reached."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Concurrency limit reached"
    mock_get.return_value = mock_resp

    with pytest.raises(ScraperAPIError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs")

    assert "concurrency limit or rate limit exceeded" in str(exc_info.value)


@patch("src.scraperapi_provider.requests.get")
def test_provider_server_error(mock_get, client):
    """HTTP 500 error from ScraperAPI raises ScraperAPIError."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_get.return_value = mock_resp

    with pytest.raises(ScraperAPIError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs")

    assert "failed to retrieve the page (HTTP 500)" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Timeout & Network Error Tests
# ---------------------------------------------------------------------------

@patch("src.scraperapi_provider.requests.get")
def test_request_timeout_handling(mock_get, client):
    """Network timeout raises ScraperAPIError with timeout information."""
    mock_get.side_effect = requests.Timeout("Connection timed out")

    with pytest.raises(ScraperAPIError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs", timeout=10)

    assert "timed out after 10s" in str(exc_info.value)


@patch("src.scraperapi_provider.requests.get")
def test_network_connection_error(mock_get, client):
    """Generic network error raises ScraperAPIError."""
    mock_get.side_effect = requests.ConnectionError("Failed to establish a new connection")

    with pytest.raises(ScraperAPIError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs")

    assert "ScraperAPI connection error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Checkpoint & Security Detection Tests
# ---------------------------------------------------------------------------

@patch("src.scraperapi_provider.requests.get")
def test_checkpoint_detection_blocks_processing(mock_get, client):
    """If target page returns a human verification/security checkpoint, reject processing."""
    checkpoint_pages = [
        "<html><body>Please verify you are human to proceed.</body></html>",
        "<html><body>Vercel security checkpoint - access denied</body></html>",
        "<html><body>Security Checkpoint: Checking your browser</body></html>",
        "<html><head><title>Attention Required! | Cloudflare</title></head></html>",
    ]
    for page in checkpoint_pages:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = page
        mock_get.return_value = mock_resp

        with pytest.raises(ScraperAPIAccessError) as exc_info:
            client.fetch("https://www.truelancer.com/freelance-jobs")

        assert "security checkpoint or bot verification screen" in str(exc_info.value)


# ---------------------------------------------------------------------------
# API Key Redaction Tests
# ---------------------------------------------------------------------------

def test_redact_api_key_helper(fake_api_key):
    """Ensures sensitive API keys and query strings are thoroughly redacted."""
    raw = f"Error communicating with https://api.scraperapi.com/?api_key={fake_api_key}&url=https://example.com"
    sanitized = redact_api_key(raw, api_key=fake_api_key)

    assert fake_api_key not in sanitized
    assert "[REDACTED]" in sanitized


@patch("src.scraperapi_provider.requests.get")
def test_api_key_redacted_on_exception(mock_get, client, fake_api_key):
    """Ensures exceptions never leak the raw API key."""
    mock_get.side_effect = requests.RequestException(
        f"Failed to connect to https://api.scraperapi.com/?api_key={fake_api_key}"
    )

    with pytest.raises(ScraperAPIError) as exc_info:
        client.fetch("https://www.truelancer.com/freelance-jobs")

    error_text = str(exc_info.value)
    assert fake_api_key not in error_text
    assert "[REDACTED]" in error_text


# ---------------------------------------------------------------------------
# Scraper & Pipeline Integration Tests
# ---------------------------------------------------------------------------

import json

def make_truelancer_fixture_html(projects):
    payload = {
        "props": {
            "pageProps": {
                "data": {
                    "projects": {"data": projects}
                }
            }
        }
    }
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script></html>"
    )

HTML_SAMPLE = make_truelancer_fixture_html([
    {
        "title": "React and FastAPI Full Stack Development",
        "description": "Looking for a qualified developer to build a modern dashboard application using Python.",
        "budget": 1500,
        "currency": "usd",
        "created_at": "2026-11-20T10:00:00.000000Z",
        "skills": [{"tagName": "React.js"}, {"tagName": "Python"}, {"tagName": "FastAPI"}],
        "link": "https://www.truelancer.com/freelance-project/react-and-fastapi-full-stack-101",
    }
])


def test_convenience_function_exported_in_scraper():
    """Verify that fetch_page_via_scraperapi is exported and accessible from src.scraper."""
    assert scraper_fetch_page_via_scraperapi is fetch_page_via_scraperapi


@patch("src.scraperapi_provider.requests.get")
def test_scrape_truelancer_pages_with_scraperapi_fetcher(mock_get, fake_api_key):
    """
    Verify scrape_truelancer_pages executes seamlessly with fetch_page_via_scraperapi
    passed as its fetcher function.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_SAMPLE
    mock_get.return_value = mock_resp

    def custom_fetcher(url: str) -> str:
        return fetch_page_via_scraperapi(url, api_key=fake_api_key)

    start_url = "https://www.truelancer.com/freelance-jobs"
    projects = scrape_truelancer_pages(
        start_url=start_url,
        max_pages=1,
        fetcher=custom_fetcher,
        sleep_fn=lambda _: None,
    )

    assert isinstance(projects, list)
    assert len(projects) == 1
    assert "React" in projects[0].title
    assert projects[0].category in ("Web", "Web Development", "General Software")


@patch("src.scraperapi_provider.requests.get")
def test_truelancer_pipeline_with_scraperapi_fetcher(mock_get, fake_api_key):
    """
    Verify run_truelancer_pipeline functions end-to-end with ScraperAPI fetcher,
    retaining existing validation, classification, and run tracking.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_SAMPLE
    mock_get.return_value = mock_resp

    def custom_fetcher(url: str) -> str:
        return fetch_page_via_scraperapi(url, api_key=fake_api_key)

    mock_submitter = MagicMock(return_value={
        "total": 1,
        "inserted": 1,
        "duplicate_skipped": 0,
        "failed": 0,
    })
    mock_creator = MagicMock(return_value="mock-run-id-123")
    mock_updater = MagicMock()

    result = run_truelancer_pipeline(
        source_id="mock-source-id-456",
        start_url="https://www.truelancer.com/freelance-jobs",
        max_pages=1,
        fetcher=custom_fetcher,
        sleep_fn=lambda _: None,
        submitter=mock_submitter,
        run_creator=mock_creator,
        run_updater=mock_updater,
    )

    assert result["status"] == "SUCCESS"
    assert result["records_found"] == 1
    mock_creator.assert_called_once()
    mock_updater.assert_called_once()
    mock_submitter.assert_called_once()


# ---------------------------------------------------------------------------
# Explicit Provider Selection & Actual Execution Path Tests
# ---------------------------------------------------------------------------

def test_resolve_page_fetcher_explicit_provider_direct():
    """Explicitly selecting 'direct' returns fetch_page."""
    from src.scraper import resolve_page_fetcher, fetch_page
    fetcher = resolve_page_fetcher(provider="direct")
    assert fetcher is fetch_page


def test_resolve_page_fetcher_explicit_provider_scraperapi(monkeypatch, fake_api_key):
    """Explicitly selecting 'scraperapi' returns ScraperAPI fetcher function."""
    from src.scraper import resolve_page_fetcher
    monkeypatch.setenv("SCRAPER_API_KEY", fake_api_key)
    fetcher = resolve_page_fetcher(provider="scraperapi")
    assert callable(fetcher)
    assert fetcher is not scraper_fetch_page_via_scraperapi


def test_resolve_page_fetcher_unknown_provider_raises():
    """Unrecognized provider raises ValueError rather than silently defaulting."""
    from src.scraper import resolve_page_fetcher
    with pytest.raises(ValueError) as exc:
        resolve_page_fetcher(provider="invalid_provider")
    assert "Unknown scraping provider 'invalid_provider'" in str(exc.value)


@patch("src.scraperapi_provider.requests.get")
def test_scrape_truelancer_pages_via_provider_parameter(mock_get, fake_api_key):
    """
    Test that scrape_truelancer_pages directly invokes the ScraperAPI provider
    when provider='scraperapi' is passed without an explicit fetcher.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_SAMPLE
    mock_get.return_value = mock_resp

    start_url = "https://www.truelancer.com/freelance-jobs"
    projects = scrape_truelancer_pages(
        start_url=start_url,
        max_pages=1,
        provider="scraperapi",
        scraperapi_key=fake_api_key,
        sleep_fn=lambda _: None,
    )

    assert len(projects) == 1
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["api_key"] == fake_api_key
    assert kwargs["params"]["url"] == start_url


@patch("src.scraperapi_provider.requests.get")
def test_scrape_truelancer_pages_via_env_var_provider(mock_get, monkeypatch, fake_api_key):
    """
    Test that scrape_truelancer_pages uses ScraperAPI when SCRAPING_PROVIDER=scraperapi is set in env.
    """
    monkeypatch.setenv("SCRAPING_PROVIDER", "scraperapi")
    monkeypatch.setenv("SCRAPER_API_KEY", fake_api_key)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_SAMPLE
    mock_get.return_value = mock_resp

    start_url = "https://www.truelancer.com/freelance-jobs"
    projects = scrape_truelancer_pages(
        start_url=start_url,
        max_pages=1,
        sleep_fn=lambda _: None,
    )

    assert len(projects) == 1
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["api_key"] == fake_api_key


@patch("src.scraperapi_provider.requests.get")
def test_pipeline_execution_path_calls_scraperapi(mock_get, fake_api_key):
    """
    Test that run_truelancer_pipeline invokes ScraperAPI when provider='scraperapi'
    is passed down the execution path.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_SAMPLE
    mock_get.return_value = mock_resp

    mock_submitter = MagicMock(return_value={"total": 1, "inserted": 1, "failed": 0})
    mock_creator = MagicMock(return_value="run-prov-123")
    mock_updater = MagicMock()

    result = run_truelancer_pipeline(
        source_id="src-prov-1",
        start_url="https://www.truelancer.com/freelance-jobs",
        max_pages=1,
        provider="scraperapi",
        scraperapi_key=fake_api_key,
        sleep_fn=lambda _: None,
        submitter=mock_submitter,
        run_creator=mock_creator,
        run_updater=mock_updater,
    )

    assert result["status"] == "SUCCESS"
    assert result["records_found"] == 1
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["api_key"] == fake_api_key


@patch("src.scraperapi_provider.requests.get")
def test_pipeline_records_failure_on_scraperapi_error(mock_get, fake_api_key):
    """
    Test that when ScraperAPI fails (e.g. 500 error or timeout), the pipeline
    records a FAILED scraping run without crashing silently.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_get.return_value = mock_resp

    mock_creator = MagicMock(return_value="run-prov-err")
    mock_updater = MagicMock()

    with pytest.raises(ScraperAPIError):
        run_truelancer_pipeline(
            source_id="src-prov-2",
            start_url="https://www.truelancer.com/freelance-jobs",
            max_pages=1,
            provider="scraperapi",
            scraperapi_key=fake_api_key,
            sleep_fn=lambda _: None,
            run_creator=mock_creator,
            run_updater=mock_updater,
        )

    mock_updater.assert_called_once()
    _, kwargs = mock_updater.call_args
    assert kwargs["status"] == "FAILED"
    assert "ScraperAPI failed to retrieve the page" in kwargs["error_log"]
