
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
            "scrapescout_test_dashboard_analytics_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        yield module, mock_create_client.return_value


class FakeQuery:
    def __init__(self, response):
        self.response = response
        self.filters = []

    def select(self, *args, **kwargs):
        self.filters.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.filters.append(("eq", args, kwargs))
        return self

    def gte(self, *args, **kwargs):
        self.filters.append(("gte", args, kwargs))
        return self

    def lt(self, *args, **kwargs):
        self.filters.append(("lt", args, kwargs))
        return self

    def execute(self):
        return self.response


def make_response(data=None, count=None):
    return SimpleNamespace(data=data, count=count)


def get_dashboard_endpoint(module):
    return next(
        route.endpoint
        for route in module.app.routes
        if getattr(route, "path", None) == "/analytics/dashboard"
    )


def test_dashboard_analytics_returns_expected_statistics(backend):
    module, mock_client = backend

    sources = [
        {
            "id": "source-1",
            "name": "Truelancer",
        },
        {
            "id": "source-2",
            "name": "PeoplePerHour",
        },
    ]

    project_counts = {
        "total": 120,
        "today": 8,
        "Web": 40,
        "App": 35,
        "Software": 30,
        "Both": 15,
        "source-1": 100,
        "source-2": 20,
    }

    # PAUSED represents an unexpected/legacy status.
    # It must be included in the total, but not in the known status counts.
    run_counts = {
        "SUCCESS": 16,
        "FAILED": 2,
        "RUNNING": 2,
        "PAUSED": 3,
    }

    def table_side_effect(table_name):
        if table_name == "sources":
            return FakeQuery(make_response(data=sources))

        if table_name == "scraping_runs":
            query = FakeQuery(make_response(count=0))

            def execute():
                status_filter = next(
                    (
                        item[1][1]
                        for item in query.filters
                        if item[0] == "eq" and item[1][0] == "status"
                    ),
                    None,
                )

                if status_filter is None:
                    return make_response(count=sum(run_counts.values()))

                return make_response(
                    count=run_counts.get(status_filter, 0)
                )

            query.execute = execute
            return query

        if table_name == "projects":
            query = FakeQuery(make_response(count=0))

            def execute():
                equality_filters = {
                    item[1][0]: item[1][1]
                    for item in query.filters
                    if item[0] == "eq"
                }

                has_date_filter = any(
                    item[0] == "gte"
                    for item in query.filters
                )

                if has_date_filter:
                    count = project_counts["today"]
                elif "project_type" in equality_filters:
                    count = project_counts.get(
                        equality_filters["project_type"],
                        0,
                    )
                elif "source_id" in equality_filters:
                    count = project_counts.get(
                        equality_filters["source_id"],
                        0,
                    )
                else:
                    count = project_counts["total"]

                return make_response(count=count)

            query.execute = execute
            return query

        raise AssertionError(f"Unexpected table: {table_name}")

    mock_client.table.side_effect = table_side_effect

    result = get_dashboard_endpoint(module)()

    assert result["total_projects"] == 120
    assert result["projects_today"] == 8

    assert result["projects_by_type"] == {
        "Web": 40,
        "App": 35,
        "Software": 30,
        "Both": 15,
    }

    assert result["projects_by_source"] == [
        {
            "source_name": "Truelancer",
            "project_count": 100,
        },
        {
            "source_name": "PeoplePerHour",
            "project_count": 20,
        },
    ]

    assert result["scraping_runs"] == {
        "total": 23,
        "successful": 16,
        "failed": 2,
        "running": 2,
    }


def test_dashboard_analytics_handles_no_sources(backend):
    module, mock_client = backend

    def table_side_effect(table_name):
        if table_name == "sources":
            return FakeQuery(make_response(data=[]))

        if table_name == "projects":
            return FakeQuery(make_response(count=0))

        if table_name == "scraping_runs":
            return FakeQuery(make_response(count=0))

        raise AssertionError(f"Unexpected table: {table_name}")

    mock_client.table.side_effect = table_side_effect

    result = get_dashboard_endpoint(module)()

    assert result["total_projects"] == 0
    assert result["projects_today"] == 0
    assert result["projects_by_source"] == []
    assert result["scraping_runs"] == {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "running": 0,
    }


def test_dashboard_analytics_handles_database_error(backend):
    module, mock_client = backend

    mock_client.table.side_effect = Exception(
        "Database unavailable"
    )

    with pytest.raises(HTTPException) as exc:
        get_dashboard_endpoint(module)()

    assert exc.value.status_code == 500

    assert exc.value.detail == (
        "Unable to fetch dashboard analytics due to a server error."
    )

    assert "Database unavailable" not in exc.value.detail
