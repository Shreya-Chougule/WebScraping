
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


# ---------------------------------------------------------------------------
# Task 6: Configuration & Lifespan Integration Tests
# ---------------------------------------------------------------------------

def test_parse_bool_env():
    from src.scheduler import parse_bool_env
    assert parse_bool_env(None, default=False) is False
    assert parse_bool_env(None, default=True) is True
    assert parse_bool_env('', default=False) is False
    assert parse_bool_env('true') is True
    assert parse_bool_env('TRUE') is True
    assert parse_bool_env('1') is True
    assert parse_bool_env('yes') is True
    assert parse_bool_env('on') is True
    assert parse_bool_env('false') is False
    assert parse_bool_env('0') is False
    assert parse_bool_env('no') is False
    assert parse_bool_env('off') is False

    with pytest.raises(ValueError):
        parse_bool_env('invalid_bool')


def test_start_scheduler_from_config_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SCHEDULER_ENABLED', raising=False)
    scheduler = scheduler_module.start_scheduler_from_config()
    assert scheduler is None
    assert scheduler_module.get_scheduler() is None


@pytest.mark.parametrize('val', ['false', 'FALSE', '0', 'no', 'off'])
def test_start_scheduler_from_config_explicitly_disabled(monkeypatch, val):
    monkeypatch.setenv('SCHEDULER_ENABLED', val)
    scheduler = scheduler_module.start_scheduler_from_config()
    assert scheduler is None
    assert scheduler_module.get_scheduler() is None


def test_start_scheduler_from_config_enabled_success(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_INTERVAL_MINUTES', '120')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'test-cfg-source')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    monkeypatch.setenv('SCHEDULER_MAX_PAGES', '2')
    monkeypatch.setenv('SCHEDULER_MIN_REQUEST_INTERVAL', '0.5')
    monkeypatch.setenv('SCRAPING_PROVIDER', 'scraperapi')

    scheduler = scheduler_module.start_scheduler_from_config()
    assert scheduler is not None
    assert scheduler.running

    job = scheduler.get_job('truelancer_scraping_job')
    assert job is not None
    assert job.trigger.interval.total_seconds() == 120 * 60
    assert job.args == ('test-cfg-source', 'https://www.truelancer.com/freelance-jobs', 2, 0.5, 'scraperapi')


def test_start_scheduler_from_config_missing_source_id_raises(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    monkeypatch.delenv('SCHEDULER_SOURCE_ID', raising=False)

    with pytest.raises(ValueError, match='SCHEDULER_SOURCE_ID is required'):
        scheduler_module.start_scheduler_from_config()


def test_start_scheduler_from_config_missing_start_url_raises(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'test-source')
    monkeypatch.delenv('SCHEDULER_START_URL', raising=False)

    with pytest.raises(ValueError, match='SCHEDULER_START_URL is required'):
        scheduler_module.start_scheduler_from_config()


def test_start_scheduler_from_config_invalid_interval_raises(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'test-source')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    monkeypatch.setenv('SCHEDULER_INTERVAL_MINUTES', '-5')

    with pytest.raises(ValueError, match='Invalid SCHEDULER_INTERVAL_MINUTES'):
        scheduler_module.start_scheduler_from_config()


def test_start_scheduler_from_config_invalid_max_pages_raises(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'test-source')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    monkeypatch.setenv('SCHEDULER_MAX_PAGES', 'not-a-number')

    with pytest.raises(ValueError, match='Invalid SCHEDULER_MAX_PAGES'):
        scheduler_module.start_scheduler_from_config()


def test_start_scheduler_from_config_invalid_min_interval_raises(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'test-source')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    monkeypatch.setenv('SCHEDULER_MIN_REQUEST_INTERVAL', '-1.0')

    with pytest.raises(ValueError, match='Invalid SCHEDULER_MIN_REQUEST_INTERVAL'):
        scheduler_module.start_scheduler_from_config()


def test_scheduled_job_forwards_provider(monkeypatch):
    mock_pipeline = Mock(return_value={'status': 'SUCCESS'})
    monkeypatch.setattr(scheduler_module, 'run_truelancer_pipeline', mock_pipeline)

    scheduler_module.scheduled_truelancer_job(
        source_id='test-src',
        start_url='https://www.truelancer.com/freelance-jobs',
        max_pages=2,
        min_request_interval=1.0,
        provider='scraperapi',
    )

    mock_pipeline.assert_called_once_with(
        source_id='test-src',
        start_url='https://www.truelancer.com/freelance-jobs',
        max_pages=2,
        min_request_interval=1.0,
        provider='scraperapi',
    )


def test_fastapi_lifespan_skips_when_disabled(monkeypatch):
    monkeypatch.delenv('SCHEDULER_ENABLED', raising=False)
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        response = client.get('/')
        assert response.status_code == 200
        assert scheduler_module.get_scheduler() is None


def test_fastapi_lifespan_starts_and_stops_scheduler(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'lifespan-src')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        response = client.get('/')
        assert response.status_code == 200
        scheduler = scheduler_module.get_scheduler()
        assert scheduler is not None
        assert scheduler.running

    # After exiting TestClient context, shutdown should stop scheduler
    assert scheduler_module.get_scheduler() is None


def test_fastapi_repeated_lifecycle_no_duplicates(monkeypatch):
    monkeypatch.setenv('SCHEDULER_ENABLED', 'true')
    monkeypatch.setenv('SCHEDULER_SOURCE_ID', 'lifespan-src')
    monkeypatch.setenv('SCHEDULER_START_URL', 'https://www.truelancer.com/freelance-jobs')
    from fastapi.testclient import TestClient
    from backend.main import app

    # First lifecycle run
    with TestClient(app) as client:
        assert scheduler_module.get_scheduler() is not None

    # Second lifecycle run
    with TestClient(app) as client:
        scheduler = scheduler_module.get_scheduler()
        assert scheduler is not None
        assert len(scheduler.get_jobs()) == 1
        assert scheduler.get_job('truelancer_scraping_job') is not None
