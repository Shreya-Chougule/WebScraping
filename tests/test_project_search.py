import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


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
            "scrapescout_test_project_search",
            main_path,
        )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        yield module, mock_create_client.return_value


@pytest.fixture
def mock_query(backend):
    """Configure a reusable mocked Supabase query."""
    _, mock_supabase = backend

    query = Mock()

    mock_supabase.table.return_value.select.return_value = query

    query.or_.return_value = query
    query.eq.return_value = query
    query.contains.return_value = query
    query.ilike.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.range.return_value = query

    return mock_supabase, query


def test_search_projects_returns_results(backend, mock_query):
    module, _ = backend
    mock_supabase, query = mock_query

    expected_data = [
        {
            "id": str(uuid4()),
            "title": "React Website Development",
            "original_url": "https://example.com/project/1",
            "project_type": "Web",
        }
    ]

    query.execute.return_value.data = expected_data

    result = module.search_projects(
        limit=20,
        offset=0,
    )

    assert result == expected_data

    mock_supabase.table.assert_called_once_with("projects")
    query.range.assert_called_once_with(0, 19)
    query.execute.assert_called_once()


def test_search_projects_applies_all_filters(backend, mock_query):
    module, _ = backend
    _, query = mock_query

    source_id = uuid4()

    query.execute.return_value.data = []

    result = module.search_projects(
        search="React developer",
        project_type="Web",
        technology="React",
        location="Pune",
        source_id=source_id,
        category="Web Development",
        limit=10,
        offset=20,
    )

    assert result == []

    query.or_.assert_called_once_with(
        'title.ilike."%React developer%",'
        'description.ilike."%React developer%"'
    )

    query.eq.assert_any_call("project_type", "Web")
    query.eq.assert_any_call("source_id", str(source_id))
    query.eq.assert_any_call("category", "Web Development")

    query.contains.assert_called_once_with(
        "required_technologies",
        ["React"],
    )

    query.ilike.assert_called_once_with(
        "location",
        "%Pune%",
    )

    query.range.assert_called_once_with(20, 29)


def test_search_projects_applies_posted_date_filters(
    backend,
    mock_query,
):
    module, _ = backend
    _, query = mock_query

    query.execute.return_value.data = []

    from_date = module.datetime.fromisoformat(
        "2026-01-01T00:00:00"
    )

    to_date = module.datetime.fromisoformat(
        "2026-01-31T23:59:59"
    )

    result = module.search_projects(
        posted_from=from_date,
        posted_to=to_date,
        limit=25,
        offset=0,
    )

    assert result == []

    query.gte.assert_called_once_with(
        "posted_date",
        from_date.isoformat(),
    )

    query.lte.assert_called_once_with(
        "posted_date",
        to_date.isoformat(),
    )


def test_search_projects_rejects_invalid_date_range(backend):
    module, mock_supabase = backend

    from_date = module.datetime.fromisoformat(
        "2026-02-01T00:00:00"
    )

    to_date = module.datetime.fromisoformat(
        "2026-01-01T00:00:00"
    )

    with pytest.raises(HTTPException) as exc_info:
        module.search_projects(
            posted_from=from_date,
            posted_to=to_date,
            limit=10,
            offset=0,
        )

    assert exc_info.value.status_code == 422

    mock_supabase.table.assert_not_called()


def test_search_projects_returns_empty_list_when_no_results(
    backend,
    mock_query,
):
    module, _ = backend
    _, query = mock_query

    query.execute.return_value.data = None

    result = module.search_projects(
        limit=10,
        offset=0,
    )

    assert result == []


def test_search_projects_handles_database_error(
    backend,
    mock_query,
):
    module, _ = backend
    _, query = mock_query

    query.execute.side_effect = Exception(
        "Database unavailable"
    )

    with pytest.raises(HTTPException) as exc_info:
        module.search_projects(
            limit=10,
            offset=0,
        )

    assert exc_info.value.status_code == 500

    assert exc_info.value.detail == (
        "Unable to search projects due to a server error."
    )

    assert "Database unavailable" not in exc_info.value.detail