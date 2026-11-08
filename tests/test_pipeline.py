
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import run_truelancer_pipeline


START_URL = "https://www.truelancer.com/projects?page=1"


def make_project():
    return Mock(title="Build a React Website")


def make_pipeline_dependencies(
    projects=None,
    submission_results=None,
):
    projects = projects if projects is not None else [make_project()]

    submission_results = (
        submission_results
        if submission_results is not None
        else {
            "total": 1,
            "inserted": 1,
            "duplicate_skipped": 0,
            "irrelevant_skipped": 0,
            "missing_url_skipped": 0,
            "source_not_found_skipped": 0,
            "invalid_skipped": 0,
            "failed": 0,
        }
    )

    creator = Mock(return_value="test-run-id")
    scraper = Mock(return_value=projects)
    submitter = Mock(return_value=submission_results)
    updater = Mock()

    return creator, scraper, submitter, updater


def run_with_dependencies(
    creator,
    scraper,
    submitter,
    updater,
):
    return run_truelancer_pipeline(
        source_id="test-source-id",
        start_url=START_URL,
        api_endpoint="http://localhost:8000/scraping-runs",
        fetcher=Mock(),
        sleep_fn=Mock(),
        run_creator=creator,
        scraper=scraper,
        submitter=submitter,
        run_updater=updater,
    )


def test_pipeline_successfully_scrapes_and_submits_projects():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    result = run_with_dependencies(
        creator,
        scraper,
        submitter,
        updater,
    )

    assert result["run_id"] == "test-run-id"
    assert result["status"] == "SUCCESS"
    assert result["records_found"] == 1
    assert result["submission"]["inserted"] == 1

    creator.assert_called_once()
    scraper.assert_called_once()
    submitter.assert_called_once()
    updater.assert_called_once()

    assert updater.call_args.kwargs["status"] == "SUCCESS"
    assert updater.call_args.kwargs["records_found"] == 1


def test_pipeline_marks_run_failed_when_submission_fails():
    submission = {
        "total": 1,
        "inserted": 0,
        "duplicate_skipped": 0,
        "irrelevant_skipped": 0,
        "missing_url_skipped": 0,
        "source_not_found_skipped": 0,
        "invalid_skipped": 0,
        "failed": 1,
    }

    creator, scraper, submitter, updater = (
        make_pipeline_dependencies(
            submission_results=submission,
        )
    )

    result = run_with_dependencies(
        creator,
        scraper,
        submitter,
        updater,
    )

    assert result["status"] == "FAILED"
    assert result["records_found"] == 1

    update_payload = updater.call_args.kwargs

    assert update_payload["status"] == "FAILED"
    assert update_payload["records_found"] == 1
    assert "submission summary" in update_payload["error_log"].lower()


def test_pipeline_marks_empty_successful_run_as_success():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies(
            projects=[],
            submission_results={
                "total": 0,
                "inserted": 0,
                "duplicate_skipped": 0,
                "irrelevant_skipped": 0,
                "missing_url_skipped": 0,
                "source_not_found_skipped": 0,
                "invalid_skipped": 0,
                "failed": 0,
            },
        )
    )

    result = run_with_dependencies(
        creator,
        scraper,
        submitter,
        updater,
    )

    assert result["status"] == "SUCCESS"
    assert result["records_found"] == 0
    submitter.assert_called_once_with([])


def test_pipeline_marks_run_failed_when_scraping_raises_error():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    scraper.side_effect = RuntimeError("Scraping failed")

    with pytest.raises(RuntimeError, match="Scraping failed"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    submitter.assert_not_called()

    assert updater.call_args.kwargs["status"] == "FAILED"
    assert updater.call_args.kwargs["records_found"] == 0
    assert "Scraping failed" in updater.call_args.kwargs["error_log"]


def test_pipeline_marks_run_failed_when_submission_raises_error():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    submitter.side_effect = RuntimeError("Submission failed")

    with pytest.raises(RuntimeError, match="Submission failed"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    assert updater.call_args.kwargs["status"] == "FAILED"
    assert updater.call_args.kwargs["records_found"] == 1


def test_pipeline_rejects_invalid_scraper_result():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    scraper.return_value = None

    with pytest.raises(ValueError, match="project list"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    submitter.assert_not_called()
    assert updater.call_args.kwargs["status"] == "FAILED"


def test_pipeline_rejects_invalid_submission_result():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    submitter.return_value = None

    with pytest.raises(ValueError, match="invalid result"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    assert updater.call_args.kwargs["status"] == "FAILED"


def test_pipeline_rejects_submission_result_without_failed_count():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies(
            submission_results={"inserted": 1},
        )
    )

    with pytest.raises(ValueError, match="failed count"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    assert updater.call_args.kwargs["status"] == "FAILED"


def test_pipeline_rejects_missing_source_id():
    with pytest.raises(ValueError, match="source_id"):
        run_truelancer_pipeline(
            source_id="",
            start_url=START_URL,
        )


def test_pipeline_rejects_missing_start_url():
    with pytest.raises(ValueError, match="start_url"):
        run_truelancer_pipeline(
            source_id="test-source-id",
            start_url="",
        )


def test_pipeline_rejects_invalid_max_pages():
    with pytest.raises(ValueError, match="max_pages"):
        run_truelancer_pipeline(
            source_id="test-source-id",
            start_url=START_URL,
            max_pages=0,
        )


def test_pipeline_rejects_negative_request_interval():
    with pytest.raises(ValueError, match="min_request_interval"):
        run_truelancer_pipeline(
            source_id="test-source-id",
            start_url=START_URL,
            min_request_interval=-1,
        )


def test_pipeline_does_not_hide_logging_failure():
    creator, scraper, submitter, updater = (
        make_pipeline_dependencies()
    )

    updater.side_effect = RuntimeError("Logging unavailable")

    with pytest.raises(RuntimeError, match="Logging unavailable"):
        run_with_dependencies(
            creator,
            scraper,
            submitter,
            updater,
        )

    assert updater.call_count == 2
