import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.extraction_schema import ExtractedProject
from src.scraperapi_provider import ScraperAPIAccessError, ScraperAPIConfigError


@pytest.fixture
def backend_app():
    main_path = BACKEND_DIR / "main.py"
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-key",
                "ENVIRONMENT": "development",
                "AUTH_REQUIRED": "true",
                "JWT_SECRET_KEY": "test-jwt-secret-key-at-least-32-bytes-long",
                "SCRAPING_PROVIDER": "scraperapi",
                "SCHEDULER_MAX_PAGES": "2",
                "SCHEDULER_MIN_REQUEST_INTERVAL": "0.5",
            },
        ),
        patch("backend.supabase_client.create_client") as mock_create_client,
    ):
        spec = importlib.util.spec_from_file_location(
            "scrapescout_test_manual_fetch_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module, mock_create_client.return_value, TestClient(module.app)


def make_auth_header(module, role="admin"):
    user = {
        "sub": str(uuid4()),
        "email": f"{role}@scrapescout.com",
        "role": role,
        "full_name": f"Test {role.title()}",
    }
    token = module.create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


class FakeTableQuery:
    def __init__(self, handler):
        self.handler = handler
        self.op = "select"
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def insert(self, data):
        self.op = "insert"
        self.payload = data
        return self

    def update(self, data):
        self.op = "update"
        self.payload = data
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def execute(self):
        return self.handler(self.op, self.payload, self.filters)


def make_extracted_project(
    title="Build React & FastAPI Dashboard",
    url="https://www.truelancer.com/freelance-project/react-fastapi-1",
    is_relevant=True,
):
    return ExtractedProject(
        title=title,
        description="Looking for a full-stack React and FastAPI developer.",
        project_type="Web",
        technologies=["React", "FastAPI"],
        client_name="Acme Studio",
        location="Remote",
        budget="1200",
        currency="USD",
        posted_date="2026-11-20",
        deadline="Not specified",
        source_name="Truelancer",
        original_url=url,
        contact_info="Not specified",
        category="Web Development",
        confidence_score=0.92,
        is_relevant=is_relevant,
    )


def test_manual_fetch_requires_authentication(backend_app):
    _, _, client = backend_app
    response = client.post("/scrape/truelancer/manual")
    assert response.status_code == 401


def test_manual_fetch_allows_authenticated_viewer(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="viewer")
    truelancer_id = str(uuid4())

    mock_client.table.side_effect = lambda name: FakeTableQuery(
        lambda op, payload, filters: SimpleNamespace(
            data=[{
                "id": truelancer_id,
                "name": "Truelancer",
                "base_url": "https://www.truelancer.com",
                "is_active": True,
            }]
        )
    )

    with patch.object(
        module,
        "run_truelancer_pipeline",
        return_value={
            "run_id": str(uuid4()),
            "status": "SUCCESS",
            "records_found": 0,
            "submission": {"inserted": 0, "failed": 0},
        },
    ):
        response = client.post("/scrape/truelancer/manual", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_admin_only_delete_project_remains_protected_for_viewer(backend_app):
    module, _, client = backend_app
    headers = make_auth_header(module, role="viewer")
    response = client.delete(f"/projects/{uuid4()}", headers=headers)
    assert response.status_code == 403


def test_manual_fetch_returns_404_when_truelancer_missing(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="admin")

    mock_client.table.side_effect = lambda name: FakeTableQuery(
        lambda op, payload, filters: SimpleNamespace(
            data=[{"id": "s-other", "name": "Sample Job Board", "is_active": False}]
        )
    )

    response = client.post("/scrape/truelancer/manual", headers=headers)
    assert response.status_code == 404
    assert "not configured" in response.json()["detail"].lower()


def test_manual_fetch_returns_400_when_truelancer_inactive(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="admin")

    mock_client.table.side_effect = lambda name: FakeTableQuery(
        lambda op, payload, filters: SimpleNamespace(
            data=[{
                "id": "source-truelancer-1",
                "name": "Truelancer",
                "base_url": "https://www.truelancer.com",
                "is_active": False,
            }]
        )
    )

    response = client.post("/scrape/truelancer/manual", headers=headers)
    assert response.status_code == 400
    assert "inactive" in response.json()["detail"].lower()


def test_manual_fetch_runs_pipeline_and_assigns_source_id(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="admin")

    truelancer_id = str(uuid4())
    run_id = str(uuid4())
    inserted_projects = []
    run_updates = []

    existing_projects = [
        {
            "id": str(uuid4()),
            "title": "Existing Duplicate Project",
            "description": "Already stored",
            "original_url": "https://www.truelancer.com/freelance-project/dup-1",
        }
    ]

    def table_side_effect(table_name):
        if table_name == "sources":
            return FakeTableQuery(
                lambda op, payload, filters: SimpleNamespace(
                    data=[{
                        "id": truelancer_id,
                        "name": "Truelancer",
                        "base_url": "https://www.truelancer.com",
                        "is_active": True,
                    }]
                )
            )
        if table_name == "scraping_runs":
            def handle_runs(op, payload, filters):
                if op == "insert":
                    return SimpleNamespace(data=[{"id": run_id, **payload}])
                if op == "update":
                    run_updates.append((filters, payload))
                    return SimpleNamespace(data=[{"id": run_id, **payload}])
                return SimpleNamespace(data=[])
            return FakeTableQuery(handle_runs)
        if table_name == "projects":
            def handle_projects(op, payload, filters):
                if op == "select":
                    return SimpleNamespace(data=list(existing_projects))
                if op == "insert":
                    inserted_projects.append(payload)
                    return SimpleNamespace(data=[{"id": str(uuid4()), **payload}])
                return SimpleNamespace(data=[])
            return FakeTableQuery(handle_projects)
        if table_name == "notifications":
            return FakeTableQuery(lambda op, payload, filters: SimpleNamespace(data=[]))
        raise AssertionError(f"Unexpected table: {table_name}")

    mock_client.table.side_effect = table_side_effect

    scraped_batch = [
        make_extracted_project(
            title="New React Opportunity",
            url="https://www.truelancer.com/freelance-project/new-1",
            is_relevant=True,
        ),
        make_extracted_project(
            title="Existing Duplicate Project",
            url="https://www.truelancer.com/freelance-project/dup-1",
            is_relevant=True,
        ),
        make_extracted_project(
            title="Logo Design Needed",
            url="https://www.truelancer.com/freelance-project/logo-1",
            is_relevant=False,
        ),
        make_extracted_project(
            title="Missing URL Web App",
            url="Not specified",
            is_relevant=True,
        ),
    ]

    with patch.object(module, "run_truelancer_pipeline") as mock_pipeline:
        def fake_pipeline(**kwargs):
            created_run_id = kwargs["run_creator"](
                source_id=kwargs["source_id"],
                api_endpoint="",
            )
            submission = kwargs["submitter"](scraped_batch)
            kwargs["run_updater"](
                run_id=created_run_id,
                status="SUCCESS",
                records_found=len(scraped_batch),
                error_log=None,
                api_endpoint="",
            )
            return {
                "run_id": created_run_id,
                "status": "SUCCESS",
                "records_found": len(scraped_batch),
                "submission": submission,
            }

        mock_pipeline.side_effect = fake_pipeline

        response = client.post(
            "/scrape/truelancer/manual",
            headers=headers,
            json={"max_pages": 2, "min_request_interval": 0.5},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["source_id"] == truelancer_id
    assert body["source_name"] == "Truelancer"
    assert body["provider"] == "scraperapi"
    assert body["start_url"] == "https://www.truelancer.com/freelance-jobs"
    assert body["status"] == "SUCCESS"
    assert body["records_found"] == 4
    assert body["inserted"] == 1
    assert body["duplicate_skipped"] == 1
    assert body["irrelevant_skipped"] == 1
    assert body["missing_url_skipped"] == 1
    assert body["failed"] == 0

    assert len(inserted_projects) == 1
    assert inserted_projects[0]["source_id"] == truelancer_id
    assert len(run_updates) == 1
    assert run_updates[0][1]["status"] == "SUCCESS"


def test_manual_fetch_handles_missing_scraperapi_key_and_redacts(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="admin")

    mock_client.table.side_effect = lambda name: FakeTableQuery(
        lambda op, payload, filters: SimpleNamespace(
            data=[{
                "id": str(uuid4()),
                "name": "Truelancer",
                "base_url": "https://www.truelancer.com",
                "is_active": True,
            }]
        )
    )

    with patch.object(
        module,
        "run_truelancer_pipeline",
        side_effect=ScraperAPIConfigError("SCRAPER_API_KEY is missing"),
    ):
        response = client.post("/scrape/truelancer/manual", headers=headers)

    assert response.status_code == 503
    assert "SCRAPER_API_KEY" in response.json()["detail"]


def test_manual_fetch_handles_provider_access_error_with_redaction(backend_app):
    module, mock_client, client = backend_app
    headers = make_auth_header(module, role="admin")

    mock_client.table.side_effect = lambda name: FakeTableQuery(
        lambda op, payload, filters: SimpleNamespace(
            data=[{
                "id": str(uuid4()),
                "name": "Truelancer",
                "base_url": "https://www.truelancer.com",
                "is_active": True,
            }]
        )
    )

    with patch.object(
        module,
        "run_truelancer_pipeline",
        side_effect=ScraperAPIAccessError(
            "Access blocked for https://api.scraperapi.com/?api_key=SECRET123&url=https://www.truelancer.com"
        ),
    ):
        response = client.post("/scrape/truelancer/manual", headers=headers)

    assert response.status_code == 502
    assert "SECRET123" not in response.json()["detail"]
    assert "[REDACTED]" in response.json()["detail"]
