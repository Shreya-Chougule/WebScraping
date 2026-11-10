
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch
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
            "scrapescout_test_keyword_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        yield module, mock_create_client.return_value


def test_get_keywords_returns_database_records(backend):
    module, mock_supabase = backend
    records = [
        {
            "id": str(uuid4()),
            "phrase": "React",
            "category": "Web",
            "is_active": True,
        }
    ]

    mock_supabase.table.return_value.select.return_value.execute.return_value.data = records

    result = module.get_keywords()

    assert result == records


def test_get_keywords_returns_empty_list(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.select.return_value.execute.return_value.data = None

    assert module.get_keywords() == []


def test_get_keywords_handles_database_error(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.select.return_value.execute.side_effect = (
        Exception("Database unavailable")
    )

    with pytest.raises(HTTPException) as exc:
        module.get_keywords()

    assert exc.value.status_code == 500


def test_create_keyword_maps_keyword_to_phrase(backend):
    module, mock_supabase = backend
    keyword_id = str(uuid4())

    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": keyword_id,
            "phrase": "React",
            "category": "Web",
            "is_active": True,
        }
    ]

    result = module.create_keyword(
        module.KeywordCreate(keyword="React", category="Web")
    )

    inserted_data = mock_supabase.table.return_value.insert.call_args.args[0]

    assert inserted_data["phrase"] == "React"
    assert "keyword" not in inserted_data
    assert result["phrase"] == "React"


def test_create_keyword_defaults_active_to_true(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": str(uuid4()),
            "phrase": "Python",
            "category": None,
            "is_active": True,
        }
    ]

    keyword = module.KeywordCreate(keyword="Python")

    module.create_keyword(keyword)

    inserted_data = mock_supabase.table.return_value.insert.call_args.args[0]

    assert inserted_data["is_active"] is True


def test_create_keyword_duplicate_returns_409(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.insert.return_value.execute.side_effect = (
        Exception("duplicate key value violates unique constraint")
    )

    with pytest.raises(HTTPException) as exc:
        module.create_keyword(module.KeywordCreate(keyword="React"))

    assert exc.value.status_code == 409


def test_create_keyword_without_response_data_returns_500(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []

    with pytest.raises(HTTPException) as exc:
        module.create_keyword(module.KeywordCreate(keyword="React"))

    assert exc.value.status_code == 500


def test_create_keyword_database_error_returns_500(backend):
    module, mock_supabase = backend

    mock_supabase.table.return_value.insert.return_value.execute.side_effect = (
        Exception("Database unavailable")
    )

    with pytest.raises(HTTPException) as exc:
        module.create_keyword(module.KeywordCreate(keyword="React"))

    assert exc.value.status_code == 500


def test_keyword_response_maps_phrase_to_keyword(backend):
    module, _ = backend

    keyword_id = uuid4()

    result = module.KeywordResponse.model_validate(
        {
            "id": keyword_id,
            "phrase": "React",
            "category": "Web",
            "is_active": True,
        }
    )

    assert result.keyword == "React"
    assert result.id == keyword_id


# ============================================================
# PATCH KEYWORD TESTS
# ============================================================

def test_update_keyword_maps_keyword_to_phrase(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": str(keyword_id),
            "phrase": "React Native",
            "category": "App",
            "is_active": True,
        }
    ]

    result = module.update_keyword(
        keyword_id,
        module.KeywordUpdate(keyword="React Native"),
    )

    updated_data = mock_supabase.table.return_value.update.call_args.args[0]

    assert updated_data == {"phrase": "React Native"}
    assert result["phrase"] == "React Native"


def test_update_keyword_category_and_active_status(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": str(keyword_id),
            "phrase": "Python",
            "category": "Software",
            "is_active": False,
        }
    ]

    result = module.update_keyword(
        keyword_id,
        module.KeywordUpdate(category="Software", is_active=False),
    )

    updated_data = mock_supabase.table.return_value.update.call_args.args[0]

    assert updated_data == {
        "category": "Software",
        "is_active": False,
    }
    assert result["is_active"] is False


def test_update_keyword_empty_update_returns_400(backend):
    module, _ = backend
    keyword_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        module.update_keyword(
            keyword_id,
            module.KeywordUpdate(),
        )

    assert exc.value.status_code == 400


def test_update_keyword_null_keyword_returns_422(backend):
    module, _ = backend
    keyword_id = uuid4()

    with pytest.raises(HTTPException) as exc:
        module.update_keyword(
            keyword_id,
            module.KeywordUpdate(keyword=None),
        )

    assert exc.value.status_code == 422


def test_update_keyword_not_found_returns_404(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with pytest.raises(HTTPException) as exc:
        module.update_keyword(
            keyword_id,
            module.KeywordUpdate(is_active=False),
        )

    assert exc.value.status_code == 404


def test_update_keyword_duplicate_returns_409(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        Exception("duplicate key value violates unique constraint")
    )

    with pytest.raises(HTTPException) as exc:
        module.update_keyword(
            keyword_id,
            module.KeywordUpdate(keyword="React"),
        )

    assert exc.value.status_code == 409


def test_update_keyword_database_error_returns_500(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        Exception("Database unavailable")
    )

    with pytest.raises(HTTPException) as exc:
        module.update_keyword(
            keyword_id,
            module.KeywordUpdate(is_active=False),
        )

    assert exc.value.status_code == 500


# ============================================================
# DELETE KEYWORD TESTS
# ============================================================

def test_delete_keyword_success(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.delete.return_value.eq.return_value.select.return_value.execute.return_value.data = [
        {"id": str(keyword_id)}
    ]

    result = module.delete_keyword(keyword_id)

    assert result is None

    mock_supabase.table.return_value.delete.assert_called_once()


def test_delete_keyword_not_found_returns_404(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.delete.return_value.eq.return_value.select.return_value.execute.return_value.data = []

    with pytest.raises(HTTPException) as exc:
        module.delete_keyword(keyword_id)

    assert exc.value.status_code == 404


def test_delete_keyword_database_error_returns_500(backend):
    module, mock_supabase = backend
    keyword_id = uuid4()

    mock_supabase.table.return_value.delete.return_value.eq.return_value.select.return_value.execute.side_effect = (
        Exception("Database unavailable")
    )

    with pytest.raises(HTTPException) as exc:
        module.delete_keyword(keyword_id)

    assert exc.value.status_code == 500
