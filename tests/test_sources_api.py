
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import main as main_module


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeQuery:
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error
        self.filters = []
        self.inserted_data = None
        self.updated_data = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        self.filters.append((args, kwargs))
        return self

    def insert(self, data):
        self.inserted_data = data
        return self

    def update(self, data):
        self.updated_data = data
        return self

    def execute(self):
        if self.error:
            raise self.error
        return FakeResponse(self.data)


class FakeSupabase:
    def __init__(self, query):
        self.query = query
        self.table_names = []

    def table(self, name):
        self.table_names.append(name)
        return self.query


@pytest.fixture
def source_client(monkeypatch):
    client = TestClient(main_module.app)
    yield client


def make_source(**overrides):
    source = {
        "id": str(uuid4()),
        "name": "Truelancer",
        "base_url": "https://www.truelancer.com",
        "scraping_type": "HTML",
        "scraping_rules": {},
        "frequency_minutes": 60,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    source.update(overrides)
    return source


def install_fake(monkeypatch, query):
    fake = FakeSupabase(query)
    monkeypatch.setattr(main_module, "supabase", fake)
    return fake


def test_get_sources_returns_all_sources(source_client, monkeypatch):
    sources = [
        make_source(name="Truelancer"),
        make_source(name="Guru"),
    ]
    query = FakeQuery(data=sources)
    fake = install_fake(monkeypatch, query)

    response = source_client.get("/sources")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Truelancer"
    assert fake.table_names == ["sources"]


def test_get_sources_filters_active_status(source_client, monkeypatch):
    source = make_source()
    query = FakeQuery(data=[source])
    fake = install_fake(monkeypatch, query)

    response = source_client.get("/sources?is_active=true")

    assert response.status_code == 200
    assert response.json()[0]["is_active"] is True
    assert ("is_active", True) in [
        (args[0], args[1]) for args, _ in query.filters
    ]
    assert fake.table_names == ["sources"]


def test_get_sources_returns_empty_list(source_client, monkeypatch):
    install_fake(monkeypatch, FakeQuery(data=[]))

    response = source_client.get("/sources")

    assert response.status_code == 200
    assert response.json() == []


def test_get_sources_handles_database_error(source_client, monkeypatch):
    install_fake(
        monkeypatch,
        FakeQuery(error=RuntimeError("database unavailable")),
    )

    response = source_client.get("/sources")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to fetch sources due to a server error."
    )
    assert "database unavailable" not in response.text


def test_create_source_returns_created_source(source_client, monkeypatch):
    source = make_source()
    query = FakeQuery(data=[source])
    install_fake(monkeypatch, query)

    response = source_client.post(
        "/sources",
        json={
            "name": "Truelancer",
            "base_url": "https://www.truelancer.com",
            "scraping_type": "HTML",
            "scraping_rules": {},
            "frequency_minutes": 60,
            "is_active": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == source["id"]
    assert response.json()["name"] == "Truelancer"
    assert query.inserted_data["base_url"] == (
        "https://www.truelancer.com"
    )


def test_create_source_rejects_missing_name(source_client, monkeypatch):
    install_fake(monkeypatch, FakeQuery())

    response = source_client.post(
        "/sources",
        json={
            "base_url": "https://example.com",
        },
    )

    assert response.status_code == 422


def test_create_source_rejects_empty_name(source_client, monkeypatch):
    install_fake(monkeypatch, FakeQuery())

    response = source_client.post(
        "/sources",
        json={
            "name": "",
            "base_url": "https://example.com",
        },
    )

    assert response.status_code == 422


def test_create_source_returns_conflict_on_duplicate(
    source_client,
    monkeypatch,
):
    install_fake(
        monkeypatch,
        FakeQuery(
            error=RuntimeError(
                "duplicate key value violates unique constraint"
            )
        ),
    )

    response = source_client.post(
        "/sources",
        json={
            "name": "Truelancer",
            "base_url": "https://www.truelancer.com",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This source already exists."


def test_create_source_handles_database_error(source_client, monkeypatch):
    install_fake(
        monkeypatch,
        FakeQuery(error=RuntimeError("database unavailable")),
    )

    response = source_client.post(
        "/sources",
        json={
            "name": "Example",
            "base_url": "https://example.com",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to create the source due to a server error."
    )


def test_update_source_returns_updated_source(
    source_client,
    monkeypatch,
):
    source_id = uuid4()
    source = make_source(id=str(source_id), is_active=False)
    query = FakeQuery(data=[source])
    install_fake(monkeypatch, query)

    response = source_client.patch(
        f"/sources/{source_id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert query.updated_data == {"is_active": False}


def test_update_source_rejects_invalid_uuid(source_client, monkeypatch):
    install_fake(monkeypatch, FakeQuery())

    response = source_client.patch(
        "/sources/not-a-uuid",
        json={"is_active": False},
    )

    assert response.status_code == 422


def test_update_source_rejects_empty_body(source_client, monkeypatch):
    install_fake(monkeypatch, FakeQuery())

    response = source_client.patch(
        f"/sources/{uuid4()}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "At least one field must be provided."
    )


def test_update_source_returns_404_when_missing(
    source_client,
    monkeypatch,
):
    install_fake(monkeypatch, FakeQuery(data=[]))

    response = source_client.patch(
        f"/sources/{uuid4()}",
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_update_source_returns_500_on_database_error(
    source_client,
    monkeypatch,
):
    install_fake(
        monkeypatch,
        FakeQuery(error=RuntimeError("database unavailable")),
    )

    response = source_client.patch(
        f"/sources/{uuid4()}",
        json={"is_active": False},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to update the source due to a server error."
    )
