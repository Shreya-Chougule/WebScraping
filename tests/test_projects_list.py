
import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
MAIN_PATH = BACKEND_DIR / "main.py"


@pytest.fixture
def main_module(monkeypatch):
    import os
    import sys
    from unittest.mock import patch

    monkeypatch.syspath_prepend(str(BACKEND_DIR))

    with patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        },
    ):
        spec = importlib.util.spec_from_file_location(
            "projects_list_test_main",
            MAIN_PATH,
        )
        module = importlib.util.module_from_spec(spec)

        with patch("supabase.create_client"):
            spec.loader.exec_module(module)

    return module


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, pages, calls, error=None):
        self.pages = pages
        self.calls = calls
        self.error = error
        self.offset = 0

    def select(self, *args, **kwargs):
        return self

    def range(self, start, end):
        self.offset = start
        self.calls.append((start, end))
        return self

    def execute(self):
        if self.error:
            raise self.error

        page_index = self.offset // 1000
        if page_index < len(self.pages):
            return FakeResponse(self.pages[page_index])

        return FakeResponse([])


class FakeSupabase:
    def __init__(self, pages=None, error=None):
        self.pages = pages or []
        self.error = error
        self.calls = []

    def table(self, name):
        assert name == "projects"
        return FakeQuery(self.pages, self.calls, self.error)


def test_get_projects_fetches_multiple_pages(main_module, monkeypatch):
    first_page = [{"id": index} for index in range(1000)]
    second_page = [
        {"id": 1000},
        {"id": 1001},
        {"id": 1002},
    ]

    fake = FakeSupabase(pages=[first_page, second_page])
    monkeypatch.setattr(main_module, "supabase", fake)

    projects = main_module.get_projects()

    assert len(projects) == 1003
    assert projects[0]["id"] == 0
    assert projects[-1]["id"] == 1002
    assert fake.calls == [
        (0, 999),
        (1000, 1999),
    ]


def test_get_projects_returns_empty_list(main_module, monkeypatch):
    fake = FakeSupabase(pages=[[]])
    monkeypatch.setattr(main_module, "supabase", fake)

    projects = main_module.get_projects()

    assert projects == []
    assert fake.calls == [(0, 999)]


def test_get_projects_handles_database_error(main_module, monkeypatch):
    fake = FakeSupabase(error=RuntimeError("database unavailable"))
    monkeypatch.setattr(main_module, "supabase", fake)

    with pytest.raises(HTTPException) as exc_info:
        main_module.get_projects()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == (
        "Unable to fetch projects due to a server error."
    )
