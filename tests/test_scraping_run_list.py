import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def backend():
    main_path = BACKEND_DIR / "main.py"

    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-key",
            },
        ),
        patch("supabase.create_client") as mock_create_client,
    ):
        spec = importlib.util.spec_from_file_location(
            "scrapescout_test_scraping_run_list_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        yield module, mock_create_client.return_value


@pytest.fixture
def run_data():
    return {
        "id": str(uuid4()),
        "source_id": str(uuid4()),
        "started_at": "2026-11-08T10:00:00+00:00",
        "completed_at": "2026-11-08T10:05:00+00:00",
        "status": "SUCCESS",
        "records_found": 25,
        "error_log": None,
    }


def get_endpoint(module):
    for route in module.app.routes:
        if (
            getattr(route, "path", None) == "/scraping-runs"
            and "GET" in getattr(route, "methods", set())
        ):
            return route.endpoint

    raise AssertionError("GET /scraping-runs route not found")


def setup_query(mock_client, data):
    query = MagicMock()

    table = mock_client.table.return_value
    table.select.return_value = query

    query.eq.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = SimpleNamespace(data=data)

    return query


def test_get_scraping_runs_returns_records(backend, run_data):
    module, mock_client = backend
    query = setup_query(mock_client, [run_data])

    endpoint = get_endpoint(module)

    result = endpoint(
        source_id=None,
        run_status=None,
        started_from=None,
        started_to=None,
        limit=50,
        offset=0,
    )

    assert result == [run_data]
    mock_client.table.assert_called_once_with("scraping_runs")
    query.order.assert_called_once_with("started_at", desc=True)
    query.range.assert_called_once_with(0, 49)


def test_get_scraping_runs_filters_by_source(backend, run_data):
    module, mock_client = backend
    query = setup_query(mock_client, [run_data])

    source_id = uuid4()
    endpoint = get_endpoint(module)

    result = endpoint(
        source_id=source_id,
        run_status=None,
        started_from=None,
        started_to=None,
        limit=50,
        offset=0,
    )

    assert result == [run_data]
    query.eq.assert_called_once_with("source_id", str(source_id))


@pytest.mark.parametrize("run_status", ["RUNNING", "SUCCESS", "FAILED"])
def test_get_scraping_runs_filters_by_status(
    backend,
    run_data,
    run_status,
):
    module, mock_client = backend
    query = setup_query(mock_client, [run_data])

    endpoint = get_endpoint(module)

    endpoint(
        source_id=None,
        run_status=run_status,
        started_from=None,
        started_to=None,
        limit=50,
        offset=0,
    )

    query.eq.assert_called_once_with("status", run_status)


def test_get_scraping_runs_filters_by_date_range(backend, run_data):
    module, mock_client = backend
    query = setup_query(mock_client, [run_data])

    from datetime import datetime, timezone

    started_from = datetime(2026, 11, 1, tzinfo=timezone.utc)
    started_to = datetime(2026, 11, 8, tzinfo=timezone.utc)

    endpoint = get_endpoint(module)

    result = endpoint(
        source_id=None,
        run_status=None,
        started_from=started_from,
        started_to=started_to,
        limit=50,
        offset=0,
    )

    assert result == [run_data]
    query.gte.assert_called_once_with(
        "started_at",
        started_from.isoformat(),
    )
    query.lte.assert_called_once_with(
        "started_at",
        started_to.isoformat(),
    )


def test_get_scraping_runs_applies_pagination(backend):
    module, mock_client = backend
    query = setup_query(mock_client, [])

    endpoint = get_endpoint(module)

    endpoint(
        source_id=None,
        run_status=None,
        started_from=None,
        started_to=None,
        limit=10,
        offset=20,
    )

    query.range.assert_called_once_with(20, 29)


def test_get_scraping_runs_returns_empty_list(backend):
    module, mock_client = backend
    setup_query(mock_client, None)

    endpoint = get_endpoint(module)

    result = endpoint(
        source_id=None,
        run_status=None,
        started_from=None,
        started_to=None,
        limit=50,
        offset=0,
    )

    assert result == []


def test_get_scraping_runs_rejects_invalid_date_range(backend):
    module, _ = backend

    from datetime import datetime, timezone

    endpoint = get_endpoint(module)

    with pytest.raises(HTTPException) as exc:
        endpoint(
            source_id=None,
            run_status=None,
            started_from=datetime(2026, 11, 9, tzinfo=timezone.utc),
            started_to=datetime(2026, 11, 8, tzinfo=timezone.utc),
            limit=50,
            offset=0,
        )

    assert exc.value.status_code == 422


def test_get_scraping_runs_handles_database_error(backend):
    module, mock_client = backend

    query = MagicMock()
    mock_client.table.return_value.select.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.side_effect = Exception("Database unavailable")

    endpoint = get_endpoint(module)

    with pytest.raises(HTTPException) as exc:
        endpoint(
            source_id=None,
            run_status=None,
            started_from=None,
            started_to=None,
            limit=50,
            offset=0,
        )

    assert exc.value.status_code == 500