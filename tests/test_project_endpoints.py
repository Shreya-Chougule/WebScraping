
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from main import supabase


client = TestClient(app)


class FakeQuery:
    def __init__(self, response=None, error=None):
        self.response = response or SimpleNamespace(data=[])
        self.error = error
        self.operations = []

    def select(self, *args, **kwargs):
        self.operations.append(("select", args, kwargs))
        return self

    def update(self, payload):
        self.operations.append(("update", payload))
        return self

    def eq(self, field, value):
        self.operations.append(("eq", field, value))
        return self

    def execute(self):
        if self.error:
            raise self.error
        return self.response


class FakeSupabase:
    def __init__(self, query):
        self.query = query
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return self.query


def sample_project(project_id=None):
    return {
        "id": str(project_id or uuid4()),
        "title": "Build a business website",
        "original_url": "https://example.com/project/1",
        "description": "Create a responsive business website",
        "source_id": str(uuid4()),
        "project_type": "Web",
        "required_technologies": ["Python", "FastAPI"],
        "client_name": "Example Client",
        "location": "Remote",
        "budget": "500",
        "currency": "USD",
        "posted_date": "2026-11-01T10:00:00+00:00",
        "deadline": None,
        "contact_info": None,
        "category": "Web Development",
        "confidence_score": 0.95,
        "is_duplicate": False,
        "created_at": "2026-11-01T10:00:00+00:00",
    }


def test_get_project_returns_project(monkeypatch):
    project_id = uuid4()
    expected = sample_project(project_id)
    fake = FakeSupabase(FakeQuery(SimpleNamespace(data=[expected])))
    monkeypatch.setattr("main.supabase", fake)

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(project_id)
    assert response.json()["title"] == expected["title"]
    assert fake.tables == ["projects"]


def test_get_project_returns_404_when_missing(monkeypatch):
    project_id = uuid4()
    fake = FakeSupabase(FakeQuery(SimpleNamespace(data=[])))
    monkeypatch.setattr("main.supabase", fake)

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 404


def test_get_project_returns_500_on_database_error(monkeypatch):
    project_id = uuid4()
    fake = FakeSupabase(FakeQuery(error=RuntimeError("database unavailable")))
    monkeypatch.setattr("main.supabase", fake)

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 500


def test_get_project_rejects_invalid_uuid():
    response = client.get("/projects/not-a-uuid")
    assert response.status_code == 422


def test_update_project_updates_only_supplied_fields(monkeypatch):
    project_id = uuid4()
    updated = sample_project(project_id)
    updated["title"] = "Updated website project"

    query = FakeQuery(SimpleNamespace(data=[updated]))
    fake = FakeSupabase(query)
    monkeypatch.setattr("main.supabase", fake)

    response = client.patch(
        f"/projects/{project_id}",
        json={"title": "Updated website project"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated website project"

    update_operations = [
        operation for operation in query.operations
        if operation[0] == "update"
    ]
    assert update_operations == [
        ("update", {"title": "Updated website project"})
    ]


def test_update_project_rejects_empty_body():
    project_id = uuid4()
    response = client.patch(f"/projects/{project_id}", json={})
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["title", "original_url"])
def test_update_project_rejects_null_required_fields(field):
    project_id = uuid4()
    response = client.patch(
        f"/projects/{project_id}",
        json={field: None},
    )
    assert response.status_code == 422


def test_update_project_returns_404_when_missing(monkeypatch):
    project_id = uuid4()
    fake = FakeSupabase(FakeQuery(SimpleNamespace(data=[])))
    monkeypatch.setattr("main.supabase", fake)

    response = client.patch(
        f"/projects/{project_id}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 404


def test_update_project_returns_409_on_duplicate(monkeypatch):
    project_id = uuid4()
    fake = FakeSupabase(
        FakeQuery(error=RuntimeError("duplicate key value violates unique constraint"))
    )
    monkeypatch.setattr("main.supabase", fake)

    response = client.patch(
        f"/projects/{project_id}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 409


def test_update_project_returns_500_on_database_error(monkeypatch):
    project_id = uuid4()
    fake = FakeSupabase(
        FakeQuery(error=RuntimeError("database unavailable"))
    )
    monkeypatch.setattr("main.supabase", fake)

    response = client.patch(
        f"/projects/{project_id}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 500


def test_update_project_rejects_invalid_uuid():
    response = client.patch(
        "/projects/not-a-uuid",
        json={"title": "Updated title"},
    )
    assert response.status_code == 422
