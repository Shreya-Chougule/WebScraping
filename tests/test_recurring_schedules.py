import importlib.util
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src import scheduler as scheduler_module


@pytest.fixture(autouse=True)
def reset_scheduler():
    scheduler_module.stop_scheduler()
    yield
    scheduler_module.stop_scheduler()


def test_daily_schedule_next_run_calculation_asia_kolkata():
    schedule = {
        "frequency": "daily",
        "time_of_day": "09:30",
        "timezone": "Asia/Kolkata",
        "is_enabled": True,
    }
    # 2026-11-26 03:00 UTC == 08:30 IST -> next fire should be 09:30 IST == 04:00 UTC same day
    ref = datetime(2026, 11, 26, 3, 0, 0, tzinfo=timezone.utc)
    next_run = scheduler_module.calculate_next_run_time(schedule, reference_time=ref)
    assert next_run == datetime(2026, 11, 26, 4, 0, 0, tzinfo=timezone.utc)


def test_weekly_schedule_next_run_calculation():
    # 2026-11-26 is Thursday (weekday 3). Schedule for Friday (4) at 10:00 IST (04:30 UTC)
    schedule = {
        "frequency": "weekly",
        "time_of_day": "10:00",
        "weekdays": [4],
        "timezone": "Asia/Kolkata",
        "is_enabled": True,
    }
    ref = datetime(2026, 11, 26, 6, 0, 0, tzinfo=timezone.utc)
    next_run = scheduler_module.calculate_next_run_time(schedule, reference_time=ref)
    assert next_run == datetime(2026, 11, 27, 4, 30, 0, tzinfo=timezone.utc)


def test_monthly_schedule_next_run_calculation():
    schedule = {
        "frequency": "monthly",
        "time_of_day": "08:00",
        "day_of_month": 15,
        "timezone": "Asia/Kolkata",
        "is_enabled": True,
    }
    ref = datetime(2026, 11, 26, 6, 0, 0, tzinfo=timezone.utc)
    next_run = scheduler_module.calculate_next_run_time(schedule, reference_time=ref)
    # Next 15th is Dec 15 08:00 IST == Dec 15 02:30 UTC
    assert next_run == datetime(2026, 12, 15, 2, 30, 0, tzinfo=timezone.utc)


def test_custom_cron_and_interval_schedules():
    cron_sched = {
        "frequency": "custom",
        "cron_expression": "0 */6 * * *",
        "timezone": "Asia/Kolkata",
        "is_enabled": True,
    }
    ref = datetime(2026, 11, 26, 1, 0, 0, tzinfo=timezone.utc)  # 06:30 IST
    next_cron = scheduler_module.calculate_next_run_time(cron_sched, reference_time=ref)
    assert next_cron is not None
    assert next_cron > ref

    interval_sched = {
        "frequency": "custom",
        "interval_minutes": 45,
        "timezone": "Asia/Kolkata",
        "is_enabled": True,
    }
    trigger = scheduler_module.build_trigger_for_schedule(interval_sched)
    assert trigger.interval.total_seconds() == 45 * 60


def test_paused_schedule_returns_no_next_run():
    schedule = {
        "frequency": "daily",
        "time_of_day": "09:30",
        "timezone": "Asia/Kolkata",
        "is_enabled": False,
    }
    assert scheduler_module.calculate_next_run_time(schedule) is None


def test_overlap_guard_prevents_concurrent_execution():
    started = threading.Event()
    release = threading.Event()

    def slow_job():
        started.set()
        release.wait(timeout=2)
        return "done"

    results = []
    t1 = threading.Thread(
        target=lambda: results.append(scheduler_module.run_with_overlap_guard(slow_job))
    )
    t1.start()
    started.wait(timeout=1)

    second_result = scheduler_module.run_with_overlap_guard(slow_job)
    release.set()
    t1.join(timeout=2)

    assert second_result == {"skipped": True, "reason": "overlap_prevented"}
    assert "done" in results


@pytest.fixture
def schedule_api():
    main_path = BACKEND_DIR / "main.py"
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "test-key",
                "ENVIRONMENT": "development",
                "AUTH_REQUIRED": "true",
                "JWT_SECRET_KEY": "test-jwt-secret-key-at-least-32-bytes-long",
                "SCHEDULER_ENABLED": "false",
            },
        ),
        patch("backend.supabase_client.create_client") as mock_create_client,
    ):
        spec = importlib.util.spec_from_file_location(
            "scrapescout_test_schedules_backend",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module, mock_create_client.return_value, TestClient(module.app)


class InMemoryScheduleTable:
    def __init__(self, store, table_name):
        self.store = store
        self.table_name = table_name
        self.op = "select"
        self.payload = None
        self.filters = []

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def insert(self, data):
        self.op = "insert"
        self.payload = data
        return self

    def update(self, data):
        self.op = "update"
        self.payload = data
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        rows = self.store[self.table_name]
        if self.op == "select":
            matched = [
                r for r in rows
                if all(str(r.get(col)) == str(val) for col, val in self.filters)
            ]
            return SimpleNamespace(data=matched)
        if self.op == "insert":
            row = {
                "id": str(uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **self.payload,
            }
            rows.append(row)
            return SimpleNamespace(data=[row])
        if self.op == "update":
            updated = []
            for r in rows:
                if all(str(r.get(col)) == str(val) for col, val in self.filters):
                    r.update(self.payload)
                    updated.append(r)
            return SimpleNamespace(data=updated)
        if self.op == "delete":
            remaining = [
                r for r in rows
                if not all(str(r.get(col)) == str(val) for col, val in self.filters)
            ]
            self.store[self.table_name] = remaining
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[])


def test_schedule_crud_pause_resume_and_execution(schedule_api):
    module, mock_client, client = schedule_api
    source_id = str(uuid4())
    store = {
        "sources": [{
            "id": source_id,
            "name": "Truelancer",
            "base_url": "https://www.truelancer.com",
            "is_active": True,
        }],
        "scraping_schedules": [],
    }
    mock_client.table.side_effect = lambda name: InMemoryScheduleTable(store, name)

    token = module.create_access_token({
        "sub": str(uuid4()),
        "email": "viewer@scrapescout.com",
        "role": "viewer",
        "full_name": "Viewer User",
    })
    headers = {"Authorization": f"Bearer {token}"}

    # Create daily schedule
    create_resp = client.post(
        "/schedules",
        headers=headers,
        json={
            "source_id": source_id,
            "name": "Morning Truelancer Sync",
            "frequency": "daily",
            "time_of_day": "09:00",
            "timezone": "Asia/Kolkata",
            "max_pages": 3,
            "min_request_interval": 1.0,
            "is_enabled": True,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["next_run_at"] is not None
    sched_id = created["id"]

    # Pause schedule
    pause_resp = client.post(f"/schedules/{sched_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["is_enabled"] is False
    assert pause_resp.json()["next_run_at"] is None

    # Resume schedule
    resume_resp = client.post(f"/schedules/{sched_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["is_enabled"] is True
    assert resume_resp.json()["next_run_at"] is not None

    # Execute persisted schedule (success & failure)
    with patch.object(
        module,
        "run_truelancer_pipeline",
        return_value={"run_id": str(uuid4()), "status": "SUCCESS", "records_found": 2, "submission": {"inserted": 2, "failed": 0}},
    ):
        res = module._execute_persisted_schedule(sched_id)
        assert res["status"] == "SUCCESS"
        assert store["scraping_schedules"][0]["last_run_status"] == "SUCCESS"

    with patch.object(
        module,
        "run_truelancer_pipeline",
        side_effect=RuntimeError("Network timeout"),
    ):
        res_fail = module._execute_persisted_schedule(sched_id)
        assert res_fail is None
        assert store["scraping_schedules"][0]["last_run_status"] == "FAILED"
        assert "Network timeout" in store["scraping_schedules"][0]["last_error"]

    # Delete schedule
    del_resp = client.delete(f"/schedules/{sched_id}", headers=headers)
    assert del_resp.status_code == 204
    assert len(store["scraping_schedules"]) == 0
