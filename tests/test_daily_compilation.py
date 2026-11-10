
from datetime import date

import pytest
from fastapi import HTTPException

import main as main_module


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def gte(self, *args, **kwargs):
        self.calls.append(("gte", args, kwargs))
        return self

    def lt(self, *args, **kwargs):
        self.calls.append(("lt", args, kwargs))
        return self

    def or_(self, *args, **kwargs):
        self.calls.append(("or_", args, kwargs))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self

    def range(self, *args, **kwargs):
        self.calls.append(("range", args, kwargs))
        return self

    def execute(self):
        if self.error:
            raise self.error
        return FakeResponse(self.data)


class FakeSupabase:
    def __init__(self, query):
        self.query = query
        self.tables = []

    def table(self, table_name):
        self.tables.append(table_name)
        return self.query


def test_daily_opportunities_returns_compiled_projects(monkeypatch):
    projects = [
        {
            "id": "project-new",
            "title": "Newest project",
            "is_duplicate": False,
            "created_at": "2026-11-07T16:00:00+00:00",
        },
        {
            "id": "project-older",
            "title": "Older project",
            "is_duplicate": None,
            "created_at": "2026-11-07T10:00:00+00:00",
        },
    ]

    query = FakeQuery(data=projects)
    fake_supabase = FakeSupabase(query)

    monkeypatch.setattr(
        main_module,
        "supabase",
        fake_supabase,
    )

    result = main_module.get_daily_opportunities(
        target_date=date(2026, 11, 7)
    )

    assert result["date"] == "2026-11-07"
    assert result["timezone"] == "Asia/Kolkata"
    assert result["title"] == "Project Opportunities for 2026-11-07"
    assert result["is_historical"] is True
    assert result["total_projects"] == 2
    assert result["projects"] == projects
    assert fake_supabase.tables == ["projects"]

    calls = query.calls

    assert (
        "gte",
        ("created_at", "2026-11-06T18:30:00+00:00"),
        {},
    ) in calls

    assert (
        "lt",
        ("created_at", "2026-11-07T18:30:00+00:00"),
        {},
    ) in calls

    assert (
        "or_",
        ("is_duplicate.is.null,is_duplicate.eq.false",),
        {},
    ) in calls

    assert (
        "order",
        ("created_at",),
        {"desc": True},
    ) in calls

    assert (
        "order",
        ("id",),
        {"desc": False},
    ) in calls


def test_daily_opportunities_returns_empty_list(monkeypatch):
    query = FakeQuery(data=[])

    monkeypatch.setattr(
        main_module,
        "supabase",
        FakeSupabase(query),
    )

    result = main_module.get_daily_opportunities(
        target_date=date(2026, 11, 7)
    )

    assert result["total_projects"] == 0
    assert result["projects"] == []


def test_daily_opportunities_converts_database_errors_to_http_500(
    monkeypatch,
):
    query = FakeQuery(
        error=RuntimeError("database unavailable")
    )

    monkeypatch.setattr(
        main_module,
        "supabase",
        FakeSupabase(query),
    )

    with pytest.raises(HTTPException) as exc_info:
        main_module.get_daily_opportunities(
            target_date=date(2026, 11, 7)
        )

    assert exc_info.value.status_code == 500

    assert exc_info.value.detail == (
        "Unable to compile daily project opportunities due to a server error."
    )

    assert "database unavailable" not in exc_info.value.detail


def test_daily_opportunities_route_is_registered():
    route_paths = [
        route.path
        for route in main_module.app.routes
        if hasattr(route, "path")
    ]

    assert "/analytics/daily-opportunities" in route_paths
