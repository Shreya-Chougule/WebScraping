"""End-to-end ScraperAPI to Truelancer integration test.

Uses the real local Truelancer fixture and real application pipeline.
All HTTP requests are mocked. No live website or database is accessed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from src import scraper as scraper_module
from src.pipeline import run_truelancer_pipeline
from src.scraperapi_provider import SCRAPER_API_URL
from src.supabase_mapper import map_project_to_supabase
from src.truelancer_parser import parse_truelancer_html


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "test_data"
    / "truelancer_listings.html"
)

START_URL = "https://www.truelancer.com/projects"
SOURCE_ID = "test-source"
DUMMY_API_KEY = "dummy_scraperapi_test_key"


@pytest.fixture
def html_fixture():
    assert FIXTURE_PATH.exists(), "Truelancer fixture is missing."
    return FIXTURE_PATH.read_text(encoding="utf-8")


def make_response(status_code=200, text="", json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_scraperapi_truelancer_full_pipeline(html_fixture, monkeypatch):
    """Exercise the real provider, parser, pipeline and submission workflow."""

    parsed_projects = parse_truelancer_html(html_fixture)
    assert len(parsed_projects) == 15

    # Seed one existing project so the real deduplicator can skip it.
    existing_duplicate = map_project_to_supabase(
        parsed_projects[0],
        SOURCE_ID,
    )

    api_endpoint = "http://testserver/projects"
    source_endpoint = "http://testserver/sources"

    get_calls = []
    post_calls = []

    def mocked_get(url, **kwargs):
        get_calls.append((url, kwargs))

        if url == SCRAPER_API_URL:
            params = kwargs.get("params", {})
            assert params["api_key"] == DUMMY_API_KEY
            assert params["url"] == START_URL

            return make_response(
                status_code=200,
                text=html_fixture,
            )

        if url == source_endpoint:
            return make_response(
                json_data=[
                    {
                        "id": SOURCE_ID,
                        "name": "Truelancer",
                    }
                ]
            )

        if url == api_endpoint:
            return make_response(
                json_data=[existing_duplicate.copy()]
            )

        pytest.fail(f"Unexpected GET request: {url}")

    def mocked_post(url, **kwargs):
        post_calls.append((url, kwargs))
        return make_response(status_code=201, text="Created")

    # requests is shared by the scraper and provider modules.
    # All network calls are intercepted here.
    monkeypatch.setattr(
        scraper_module.requests,
        "get",
        mocked_get,
    )
    monkeypatch.setattr(
        scraper_module.requests,
        "post",
        mocked_post,
    )

    # Explicitly pass test endpoints. The original function defaults
    # were bound before the constants were patched.
    def actual_submitter(projects):
        return scraper_module.send_projects_to_api(
            projects,
            api_endpoint=api_endpoint,
            source_endpoint=source_endpoint,
        )

    create_run = MagicMock(return_value="test-run-123")
    update_run = MagicMock()

    result = run_truelancer_pipeline(
        source_id=SOURCE_ID,
        start_url=START_URL,
        max_pages=1,
        min_request_interval=0,
        provider="scraperapi",
        scraperapi_key=DUMMY_API_KEY,
        sleep_fn=lambda _: None,
        submitter=actual_submitter,
        run_creator=create_run,
        run_updater=update_run,
    )

    # Pipeline completed and parsed the complete fixture.
    assert result["status"] == "SUCCESS"
    assert result["records_found"] == 15

    # ScraperAPI was called exactly once.
    scraperapi_calls = [
        call for call in get_calls
        if call[0] == SCRAPER_API_URL
    ]
    assert len(scraperapi_calls) == 1

    # Real submission workflow used the mocked API endpoints.
    assert any(url == source_endpoint for url, _ in get_calls)
    assert any(url == api_endpoint for url, _ in get_calls)

    # Existing duplicate was skipped; other projects were submitted.
    assert len(post_calls) > 0

    for url, kwargs in post_calls:
        assert url == api_endpoint
        payload = kwargs["json"]
        assert payload["source_id"] == SOURCE_ID
        assert payload["title"]
        assert payload["original_url"]

    create_run.assert_called_once()
    update_run.assert_called()


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", __file__]))
