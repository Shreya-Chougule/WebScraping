
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.scheduler as scheduler_module


@pytest.fixture(autouse=True)
def reset_scheduler():
    """Ensure every test starts without an active scheduler."""
    scheduler_module.stop_scheduler()
    yield
    scheduler_module.stop_scheduler()


def test_scheduler_module_does_not_start_automatically():
    assert scheduler_module.get_scheduler() is None


def test_start_scheduler_creates_background_scheduler():
    scheduler = scheduler_module.start_scheduler(
        source_id="test-source",
        start_url="https://www.truelancer.com/projects",
        interval_minutes=30,
    )

    assert scheduler.running
    assert scheduler_module.get_scheduler() is scheduler

    job = scheduler.get_job("truelancer_scraping_job")
    assert job is not None
    assert job.max_instances == 1


def test_start_scheduler_does_not_create_duplicate_jobs():
    first = scheduler_module.start_scheduler(
        source_id="test-source",
        start_url="https://www.truelancer.com/projects",
        interval_minutes=30,
    )

    second = scheduler_module.start_scheduler(
        source_id="test-source",
        start_url="https://www.truelancer.com/projects",
        interval_minutes=60,
    )

    assert first is second
    assert len(second.get_jobs()) == 1
    assert second.get_job("truelancer_scraping_job") is not None


def test_scheduler_job_uses_updated_interval():
    scheduler = scheduler_module.start_scheduler(
        source_id="test-source",
        start_url="https://www.truelancer.com/projects",
        interval_minutes=45,
    )

    job = scheduler.get_job("truelancer_scraping_job")

    assert job.trigger.interval.total_seconds() == 45 * 60


def test_stop_scheduler_stops_background_scheduler():
    scheduler = scheduler_module.start_scheduler(
        source_id="test-source",
        start_url="https://www.truelancer.com/projects",
    )

    scheduler_module.stop_scheduler()

    assert not scheduler.running
    assert scheduler_module.get_scheduler() is None


def test_stop_scheduler_when_not_started():
    scheduler_module.stop_scheduler()
    assert scheduler_module.get_scheduler() is None


@pytest.mark.parametrize(
    "interval",
    [0, -1, True, 1.5],
)
def test_scheduler_rejects_invalid_interval(interval):
    with pytest.raises(ValueError, match="interval_minutes"):
        scheduler_module.start_scheduler(
            source_id="test-source",
            start_url="https://www.truelancer.com/projects",
            interval_minutes=interval,
        )


def test_scheduler_rejects_missing_source_id():
    with pytest.raises(ValueError, match="source_id"):
        scheduler_module.start_scheduler(
            source_id="",
            start_url="https://www.truelancer.com/projects",
        )


def test_scheduler_rejects_missing_start_url():
    with pytest.raises(ValueError, match="start_url"):
        scheduler_module.start_scheduler(
            source_id="test-source",
            start_url="",
        )


def test_scheduler_rejects_invalid_max_pages():
    with pytest.raises(ValueError, match="max_pages"):
        scheduler_module.start_scheduler(
            source_id="test-source",
            start_url="https://www.truelancer.com/projects",
            max_pages=0,
        )


def test_scheduler_rejects_negative_request_interval():
    with pytest.raises(ValueError, match="min_request_interval"):
        scheduler_module.start_scheduler(
            source_id="test-source",
            start_url="https://www.truelancer.com/projects",
            min_request_interval=-1,
        )


def test_scheduled_job_handles_pipeline_failure():
    pipeline = Mock(side_effect=RuntimeError("Test failure"))

    original = scheduler_module.run_truelancer_pipeline
    scheduler_module.run_truelancer_pipeline = pipeline

    try:
        result = scheduler_module.scheduled_truelancer_job(
            source_id="test-source",
            start_url="https://www.truelancer.com/projects",
        )

        assert result is None
        pipeline.assert_called_once()
    finally:
        scheduler_module.run_truelancer_pipeline = original


def test_scheduled_job_returns_pipeline_result():
    expected = {
        "run_id": "test-run",
        "status": "SUCCESS",
        "records_found": 5,
        "submission": {"inserted": 5, "failed": 0},
    }

    pipeline = Mock(return_value=expected)

    original = scheduler_module.run_truelancer_pipeline
    scheduler_module.run_truelancer_pipeline = pipeline

    try:
        result = scheduler_module.scheduled_truelancer_job(
            source_id="test-source",
            start_url="https://www.truelancer.com/projects",
        )

        assert result == expected
        pipeline.assert_called_once()
    finally:
        scheduler_module.run_truelancer_pipeline = original
