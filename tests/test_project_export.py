import csv
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app

client = TestClient(app)


class FakeQuery:
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error
        self.operations = []

    def select(self, *args, **kwargs):
        self.operations.append(("select", args, kwargs))
        return self

    def eq(self, field, value):
        self.operations.append(("eq", field, value))
        return self

    def contains(self, field, value):
        self.operations.append(("contains", field, value))
        return self

    def ilike(self, field, value):
        self.operations.append(("ilike", field, value))
        return self

    def or_(self, value):
        self.operations.append(("or", value))
        return self

    def gte(self, field, value):
        self.operations.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.operations.append(("lte", field, value))
        return self

    def range(self, start, end):
        self.operations.append(("range", start, end))
        return self

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.data)


class FakeSupabase:
    def __init__(self, query):
        self.query = query
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return self.query


def sample_project():
    return {
        "id": str(uuid4()),
        "source_id": str(uuid4()),
        "title": "Build a business website",
        "description": "Create a responsive website",
        "project_type": "Web",
        "required_technologies": ["Python", "FastAPI"],
        "client_name": "Example Client",
        "location": "Remote",
        "budget": "500",
        "currency": "USD",
        "posted_date": "2026-11-01T10:00:00+00:00",
        "deadline": None,
        "original_url": "https://example.com/project/1",
        "contact_info": None,
        "category": "Web Development",
        "confidence_score": 0.95,
        "is_duplicate": False,
        "created_at": "2026-11-01T10:00:00+00:00",
    }


def test_export_projects_returns_csv(monkeypatch):
    project = sample_project()
    query = FakeQuery(data=[project])
    fake = FakeSupabase(query)

    monkeypatch.setattr("main.supabase", fake)

    response = client.get("/projects/export")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))

    assert len(rows) == 1
    assert rows[0]["title"] == project["title"]
    assert rows[0]["project_type"] == "Web"
    assert rows[0]["required_technologies"] == '["Python", "FastAPI"]'
    assert rows[0]["original_url"] == project["original_url"]

    assert fake.tables == ["projects"]


def test_export_projects_returns_headers_when_empty(monkeypatch):
    fake = FakeSupabase(FakeQuery(data=[]))

    monkeypatch.setattr("main.supabase", fake)

    response = client.get("/projects/export")

    assert response.status_code == 200

    rows = list(csv.DictReader(io.StringIO(response.text)))

    assert rows == []

    assert "title" in response.text
    assert "original_url" in response.text


def test_export_projects_applies_filters(monkeypatch):
    source_id = uuid4()
    query = FakeQuery(data=[sample_project()])
    fake = FakeSupabase(query)

    monkeypatch.setattr("main.supabase", fake)

    response = client.get(
        "/projects/export",
        params={
            "search": "website",
            "project_type": "Web",
            "technology": "Python",
            "location": "Remote",
            "source_id": str(source_id),
            "category": "Web Development",
            "posted_from": "2026-11-01T00:00:00+00:00",
            "posted_to": "2026-11-08T23:59:59+00:00",
        },
    )

    assert response.status_code == 200

    operation_names = [
        operation[0] for operation in query.operations
    ]

    assert "or" in operation_names
    assert "eq" in operation_names
    assert "contains" in operation_names
    assert "ilike" in operation_names
    assert "gte" in operation_names
    assert "lte" in operation_names


def test_export_projects_rejects_invalid_date_range(monkeypatch):
    fake = FakeSupabase(FakeQuery(data=[]))

    monkeypatch.setattr("main.supabase", fake)

    response = client.get(
        "/projects/export",
        params={
            "posted_from": "2026-11-08T00:00:00+00:00",
            "posted_to": "2026-11-01T00:00:00+00:00",
        },
    )

    assert response.status_code == 422


def test_export_projects_returns_500_on_database_error(monkeypatch):
    fake = FakeSupabase(
        FakeQuery(
            error=RuntimeError("database unavailable")
        )
    )

    monkeypatch.setattr("main.supabase", fake)

    response = client.get("/projects/export")

    assert response.status_code == 500

    detail = response.json()["detail"]

    assert detail == (
        "Unable to export projects due to a server error."
    )

    assert "database unavailable" not in detail