"""
Comprehensive End-to-End Integration Test for ScrapeScout.

Verifies the complete pipeline:
Local fixture -> Extraction -> Validation -> Keyword Classification ->
Deduplication -> Database Mapping -> FastAPI APIs -> Auth & RBAC ->
Notifications -> Search/Filtering -> Export.
"""

import io
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from src.classifier import ProjectClassifier
from src.deduplicator import ProjectDeduplicator
from src.project_validator import validate_project
from src.supabase_mapper import map_project_to_supabase
from src.truelancer_parser import parse_truelancer_html

client = TestClient(app)


def test_end_to_end_local_fixture_pipeline():
    """Verify local HTML fixture parsing, validation, classification, deduplication, and mapping."""
    fixture_path = Path(__file__).resolve().parents[1] / "test_data" / "truelancer_listings.html"
    assert fixture_path.exists(), "Test fixture truelancer_listings.html must exist"

    html_content = fixture_path.read_text(encoding="utf-8")
    extracted_projects = parse_truelancer_html(html_content)
    assert len(extracted_projects) > 0, "Parser must extract projects from fixture"

    first_project = extracted_projects[0]
    validation_errors = validate_project(first_project)
    assert len(validation_errors) == 0, f"Extracted project should have no errors: {validation_errors}"

    # Classification test
    classifier = ProjectClassifier()
    category, confidence, is_relevant = classifier.classify(first_project.title, first_project.description)
    assert category in ("Web", "App", "Software", "Both", "Other / Irrelevant")
    assert 0.0 <= confidence <= 1.0

    # Deduplication test
    deduplicator = ProjectDeduplicator()
    # First time against empty database: not duplicate
    is_dup1, reason1 = deduplicator.is_duplicate(
        first_project.to_dict(),
        existing_projects=[],
    )
    assert is_dup1 is False

    # Second time with identical existing project: must be detected as duplicate
    is_dup2, reason2 = deduplicator.is_duplicate(
        first_project.to_dict(),
        existing_projects=[first_project.to_dict()],
    )
    assert is_dup2 is True
    assert reason2 is not None

    # Database mapping test
    source_id = str(uuid4())
    mapped_db_record = map_project_to_supabase(
        project=first_project,
        source_id=source_id,
    )
    assert mapped_db_record["title"] == first_project.title
    assert mapped_db_record["source_id"] == source_id
    assert "project_type" in mapped_db_record
    assert "required_technologies" in mapped_db_record


def test_end_to_end_api_auth_and_rbac_flow():
    """Verify login, JWT retrieval, current-user me endpoint, viewer restrictions, and logout."""
    # 1. Login as admin
    admin_login_res = client.post("/auth/login", json={
        "email": "admin@scrapescout.com",
        "password": "Admin@123",
    })
    assert admin_login_res.status_code == 200
    admin_data = admin_login_res.json()
    admin_token = admin_data["access_token"]
    assert admin_data["user"]["role"] == "admin"

    # 2. Access /auth/me with admin token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@scrapescout.com"

    # 3. Login as viewer
    viewer_login_res = client.post("/auth/login", json={
        "email": "viewer@scrapescout.com",
        "password": "Viewer@123",
    })
    assert viewer_login_res.status_code == 200
    viewer_data = viewer_login_res.json()
    viewer_token = viewer_data["access_token"]
    assert viewer_data["user"]["role"] == "viewer"

    # 4. Viewer is forbidden from admin user listing
    viewer_users_res = client.get("/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_users_res.status_code == 403

    # 5. Admin is allowed to list users
    admin_users_res = client.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_users_res.status_code == 200

    # 6. Viewer is forbidden from deleting a project
    project_id = str(uuid4())
    del_res = client.delete(f"/projects/{project_id}", headers={"Authorization": f"Bearer {viewer_token}"})
    assert del_res.status_code == 403

    # 7. Logout
    logout_res = client.post("/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})
    assert logout_res.status_code == 200


def test_end_to_end_search_filter_and_export_flow(monkeypatch):
    """Verify search, multi-filter criteria matching, and CSV / Excel export consistency."""
    sample_records = [
        {
            "id": str(uuid4()),
            "source_id": str(uuid4()),
            "title": "React Dashboard with FastAPI",
            "description": "Full-stack web application development",
            "project_type": "Web",
            "required_technologies": ["React", "FastAPI"],
            "client_name": "Test Client",
            "location": "Remote",
            "budget": "1000",
            "currency": "USD",
            "posted_date": "2026-11-10T12:00:00+00:00",
            "deadline": None,
            "original_url": "https://example.com/project/react-fastapi",
            "contact_info": None,
            "category": "Web Development",
            "confidence_score": 0.98,
            "is_duplicate": False,
            "created_at": "2026-11-10T12:00:00+00:00",
        }
    ]

    class FakeQuery:
        def __init__(self, data):
            self.data = data
        def select(self, *args, **kwargs): return self
        def eq(self, *args, **kwargs): return self
        def contains(self, *args, **kwargs): return self
        def ilike(self, *args, **kwargs): return self
        def or_(self, *args, **kwargs): return self
        def gte(self, *args, **kwargs): return self
        def lte(self, *args, **kwargs): return self
        def range(self, *args, **kwargs): return self
        def execute(self): return SimpleNamespace(data=self.data)

    class FakeSupabase:
        def table(self, name): return FakeQuery(sample_records)

    monkeypatch.setattr("main.supabase", FakeSupabase())

    # Search endpoint
    search_res = client.get("/projects/search?search=FastAPI&project_type=Web")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) == 1
    assert results[0]["title"] == "React Dashboard with FastAPI"

    # CSV Export
    csv_res = client.get("/projects/export?search=FastAPI&project_type=Web&format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "React Dashboard with FastAPI" in csv_res.text

    # Excel Export
    excel_res = client.get("/projects/export?search=FastAPI&project_type=Web&format=excel")
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(excel_res.content)) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "React Dashboard with FastAPI" in sheet


def test_end_to_end_notifications_flow():
    """Verify notification lifecycle: admin creation, listing, mark read, and mark all read."""
    admin_login_res = client.post("/auth/login", json={
        "email": "admin@scrapescout.com",
        "password": "Admin@123",
    })
    admin_token = admin_login_res.json()["access_token"]

    # 1. Admin creates a system notification
    create_res = client.post(
        "/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "System Lead Discovered",
            "message": "A high-priority freelance lead was discovered.",
            "type": "high_priority",
        },
    )
    assert create_res.status_code == 201
    notif_id = create_res.json()["id"]

    # 2. List notifications
    list_res = client.get("/notifications", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert any(n["id"] == notif_id for n in data["notifications"])

    # 3. Mark individual notification as read
    read_res = client.patch(
        f"/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert read_res.status_code == 200
    assert read_res.json()["status"] == "success"

    # 4. Mark all as read
    read_all_res = client.post("/notifications/read-all", headers={"Authorization": f"Bearer {admin_token}"})
    assert read_all_res.status_code == 200
    assert read_all_res.json()["status"] == "success"
