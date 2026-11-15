
import os
import sys
import io
import csv
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app
from security import sanitize_csv_cell, is_rate_limited, reset_rate_limits

client = TestClient(app)


def test_sanitize_csv_cell_escapes_formulas():
    # OWASP formula injection trigger characters
    malicious_inputs = [
        "=1+1",
        "-5+2",
        "+cmd|' /C calc'!A0",
        "@SUM(1,1)",
        "\tmalicious_tab",
        "\rmalicious_return",
    ]
    for text in malicious_inputs:
        sanitized = sanitize_csv_cell(text)
        assert sanitized.startswith("'"), f"Failed to sanitize: {text}"
        assert sanitized == f"'{text}"


def test_sanitize_csv_cell_preserves_normal_text():
    normal_texts = [
        "React Frontend Developer",
        "Flutter Mobile App",
        "https://example.com/project",
        "Remote",
    ]
    for text in normal_texts:
        assert sanitize_csv_cell(text) == text


def test_export_csv_sanitizes_formula_injection(monkeypatch):
    malicious_title = "=cmd|' /C calc'!A0"
    project = {
        "id": str(uuid4()),
        "title": malicious_title,
        "original_url": "https://example.com/project",
        "project_type": "Web",
        "created_at": "2026-11-01T10:00:00Z",
    }

    class FakeQuery:
        def select(self, *args, **kwargs):
            return self
        def range(self, *args, **kwargs):
            return self
        def execute(self):
            return SimpleNamespace(data=[project])

    class FakeSupabase:
        def table(self, name):
            return FakeQuery()

    monkeypatch.setattr("main.supabase", FakeSupabase())

    response = client.get("/projects/export")
    assert response.status_code == 200

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    # Title must be escaped with leading single quote
    assert rows[0]["title"] == f"'{malicious_title}"


def test_rate_limiter_allows_and_blocks():
    reset_rate_limits()
    client_ip = f"test-ip-{uuid4().hex[:6]}"

    # Allowed up to limit (e.g. 5 requests)
    for _ in range(5):
        assert is_rate_limited(client_ip, bucket="test", limit=5, window_seconds=10) is False

    # Exceeding limit blocks request
    assert is_rate_limited(client_ip, bucket="test", limit=5, window_seconds=10) is True


def test_search_projects_validates_pagination_limit():
    # Negative or 0 limit is rejected
    response = client.get("/projects/search?limit=0")
    assert response.status_code == 422

    # Limit > 100 is rejected
    response = client.get("/projects/search?limit=101")
    assert response.status_code == 422


def test_test_db_returns_only_safe_status_without_leaking_records(monkeypatch):
    class FakeSelectQuery:
        def select(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def execute(self):
            return SimpleNamespace(data=[{"id": "p-1", "title": "Confidential Project", "budget": "10000 USD"}])

    class FakeSupabase:
        def table(self, name):
            return FakeSelectQuery()

    monkeypatch.setattr("main.supabase", FakeSupabase())

    response = client.get("/test-db")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["connected"] is True
    assert data["message"] == "Database connection healthy."

    # Critical security assertion: must NOT leak database records
    assert "data" not in data
    assert "Confidential Project" not in response.text


def test_test_db_database_error_does_not_leak_internals(monkeypatch):
    class ErrorQuery:
        def select(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def execute(self):
            raise RuntimeError("Database credentials host=secret.supabase.co failed")

    class FakeSupabase:
        def table(self, name):
            return ErrorQuery()

    monkeypatch.setattr("main.supabase", FakeSupabase())

    response = client.get("/test-db")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert data["connected"] is False
    assert data["message"] == "Database connection failed."

    # Must not leak database error details or hostnames
    assert "secret.supabase.co" not in response.text
