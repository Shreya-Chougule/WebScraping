
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def backend():
    """Load the backend with a mocked Supabase client."""
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
            "scrapescout_test_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        yield module, mock_create_client.return_value


def test_create_scraping_run_endpoint(backend):
    module, mock_supabase = backend
    source_id = uuid4()
    run_id = uuid4()

    expected_data = {
        "id": str(run_id),
        "source_id": str(source_id),
        "status": "RUNNING",
    }

    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        expected_data
    ]

    request = module.ScrapingRunCreate(source_id=source_id)

    result = module.create_scraping_run_endpoint(request)

    assert result == expected_data
    mock_supabase.table.assert_called_once_with("scraping_runs")

    inserted_data = (
        mock_supabase.table.return_value
        .insert.call_args.args[0]
    )

    assert inserted_data["source_id"] == str(source_id)
    assert inserted_data["status"] == "RUNNING"


def test_update_scraping_run_endpoint(backend):
    module, mock_supabase = backend
    run_id = str(uuid4())

    expected_data = {
        "id": run_id,
        "status": "SUCCESS",
        "records_found": 15,
        "error_log": None,
    }

    (
        mock_supabase.table.return_value
        .update.return_value
        .eq.return_value
        .execute.return_value.data
    ) = [expected_data]

    request = module.ScrapingRunUpdate(
        status="SUCCESS",
        records_found=15,
    )

    result = module.update_scraping_run_endpoint(
        run_id,
        request,
    )

    assert result == expected_data

    mock_supabase.table.assert_called_once_with("scraping_runs")

    update_data = (
        mock_supabase.table.return_value
        .update.call_args.args[0]
    )

    assert update_data["status"] == "SUCCESS"
    assert update_data["records_found"] == 15
    assert "completed_at" in update_data


def test_update_scraping_run_endpoint_returns_404(backend):
    module, mock_supabase = backend

    (
        mock_supabase.table.return_value
        .update.return_value
        .eq.return_value
        .execute.return_value.data
    ) = []

    request = module.ScrapingRunUpdate(
        status="FAILED",
        records_found=0,
        error_log="Test failure",
    )

    with pytest.raises(HTTPException) as exc_info:
        module.update_scraping_run_endpoint(
            str(uuid4()),
            request,
        )

    assert exc_info.value.status_code == 404


def test_scraping_run_patch_rejects_malformed_uuid(backend):
    module, _ = backend
    client = TestClient(module.app)

    response = client.patch(
        "/scraping-runs/not-a-valid-uuid",
        json={
            "status": "SUCCESS",
            "records_found": 10,
        },
    )

    assert response.status_code == 422


def test_scraping_run_patch_rejects_invalid_status(backend):
    module, _ = backend
    client = TestClient(module.app)

    response = client.patch(
        f"/scraping-runs/{uuid4()}",
        json={
            "status": "RUNNING",
            "records_found": 10,
        },
    )

    assert response.status_code == 422


def test_scraping_run_patch_rejects_negative_records_found(backend):
    module, _ = backend
    client = TestClient(module.app)

    response = client.patch(
        f"/scraping-runs/{uuid4()}",
        json={
            "status": "FAILED",
            "records_found": -1,
        },
    )

    assert response.status_code == 422


def test_scraping_run_create_rejects_missing_source_id(backend):
    module, _ = backend
    client = TestClient(module.app)

    response = client.post(
        "/scraping-runs",
        json={
            "status": "RUNNING",
        },
    )

    assert response.status_code == 422


def test_scraping_run_create_rejects_invalid_source_id(backend):
    module, _ = backend
    client = TestClient(module.app)

    response = client.post(
        "/scraping-runs",
        json={
            "source_id": "not-a-uuid",
            "status": "RUNNING",
        },
    )

    assert response.status_code == 422
