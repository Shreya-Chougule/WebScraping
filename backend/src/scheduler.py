"""
ScrapeScout scheduler.

The scheduler does not start automatically on import.
Call start_scheduler() or start_scheduler_from_config() explicitly when scheduling is required.

Timezone: Asia/Kolkata
Execution reliability:
- Single-instance execution (max_instances=1)
- Coalescing of missed executions (coalesce=True)
- Misfire grace time (misfire_grace_time=300)
- Isolated failure handling (exceptions logged, does not terminate future schedules)
"""

import os
import math
import logging
import threading
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def _validate_provider(provider: str) -> str:
    """Validate that the provider is one of the allowed values.

    Returns the normalized lower‑case provider name.
    Raises ValueError for any other value.
    """
    if not isinstance(provider, str):
        raise ValueError(f"Provider must be a string, got {type(provider).__name__}")
    normalized = provider.strip().lower()
    if normalized not in ("direct", "scraperapi"):
        raise ValueError(
            f"Invalid SCRAPING_PROVIDER: '{provider}'. Allowed values are 'direct' or 'scraperapi'."
        )
    return normalized

from typing import Optional, Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

try:
    from src.pipeline import run_truelancer_pipeline
except ImportError:
    from backend.src.pipeline import run_truelancer_pipeline


logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None
_execution_lock = threading.Lock()


def parse_bool_env(value: Optional[str], default: bool = False) -> bool:
    """
    Parse a boolean environment variable case-insensitively.
    Accepts 'true', '1', 'yes', 'on' as True.
    Accepts 'false', '0', 'no', 'off' as False.
    Returns default if value is None or empty.
    Raises ValueError on unrecognized non-empty strings.
    """
    if value is None:
        return default
    cleaned = value.strip().lower()
    if not cleaned:
        return default
    if cleaned in ("true", "1", "yes", "on"):
        return True
    if cleaned in ("false", "0", "no", "off"):
        return False
    raise ValueError(
        f"Invalid boolean environment setting '{value}'. "
        "Expected 'true'/'false' or '1'/'0'."
    )


def scheduled_truelancer_job(
    source_id: str,
    start_url: str,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
    provider: Optional[str] = None,
):
    """
    Execute one scheduled Truelancer pipeline run.
    Forwards the selected provider (e.g. 'direct' or 'scraperapi') to the pipeline.
    Catches and logs all errors so a failure never stops future scheduled executions.
    """
    try:
        logger.info("Starting scheduled Truelancer pipeline.")

        # Resolve provider from argument or environment variable and validate
        raw_provider = provider or os.getenv("SCRAPING_PROVIDER", "direct")
        resolved_provider = _validate_provider(raw_provider)


        result = run_truelancer_pipeline(
            source_id=source_id,
            start_url=start_url,
            max_pages=max_pages,
            min_request_interval=min_request_interval,
            provider=resolved_provider,
        )

        logger.info(
            "Scheduled pipeline finished with status: %s",
            result.get("status") if isinstance(result, dict) else "UNKNOWN",
        )

        return result

    except Exception:
        logger.exception("Scheduled Truelancer pipeline failed.")
        return None


def start_scheduler(
    source_id: str,
    start_url: str,
    interval_minutes: int = 60,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
    provider: Optional[str] = None,
) -> BackgroundScheduler:
    """
    Start the background scheduler and register one interval job.

    Repeated calls reuse the existing scheduler and update the job.
    """
    global _scheduler

    if not source_id or not isinstance(source_id, str):
        raise ValueError("A valid source_id is required.")

    if not start_url or not isinstance(start_url, str):
        raise ValueError("A valid start_url is required.")

    # Validate interval_minutes (positive integer, not bool)
    if not isinstance(interval_minutes, int) or isinstance(interval_minutes, bool) or interval_minutes < 1:
        raise ValueError("interval_minutes must be a positive integer.")

    # Validate max_pages (positive integer, not bool)
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer.")

    # Validate min_request_interval (numeric, finite, non‑negative, not bool)
    if isinstance(min_request_interval, bool):
        raise ValueError("min_request_interval must be a number, not boolean.")
    try:
        min_val = float(min_request_interval)
    except (TypeError, ValueError):
        raise ValueError("min_request_interval must be a numeric value.")
    if min_val < 0 or not math.isfinite(min_val):
        raise ValueError("min_request_interval must be a non‑negative finite number.")
    # Use validated float
    min_request_interval = min_val

    if _scheduler is None or not _scheduler.running:
        _scheduler = BackgroundScheduler(
            timezone="Asia/Kolkata"
        )

    job_id = "truelancer_scraping_job"

    _scheduler.add_job(
        scheduled_truelancer_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        args=[
            source_id,
            start_url,
            max_pages,
            min_request_interval,
            provider,
        ],
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    if not _scheduler.running:
        _scheduler.start()

    logger.info(
        "Scheduler started. Truelancer job interval: %s minutes.",
        interval_minutes,
    )

    return _scheduler


def start_scheduler_from_config() -> Optional[BackgroundScheduler]:
    """
    Initialize and start the scheduler based on environment configuration.

    Configuration environment variables:
    - SCHEDULER_ENABLED: 'true'/'false' (default: 'false')
    - SCHEDULER_INTERVAL_MINUTES: positive integer (default: 60)
    - SCHEDULER_SOURCE_ID: required when enabled
    - SCHEDULER_START_URL: required when enabled
    - SCHEDULER_MAX_PAGES: positive integer (default: 3)
    - SCHEDULER_MIN_REQUEST_INTERVAL: non-negative float (default: 1.0)
    - SCRAPING_PROVIDER: 'direct' or 'scraperapi' (default: 'direct')

    Returns:
        The running BackgroundScheduler instance if SCHEDULER_ENABLED is True,
        or None if disabled.

    Raises:
        ValueError: If SCHEDULER_ENABLED is True but required configuration is missing or invalid.
    """
    is_enabled = parse_bool_env(os.getenv("SCHEDULER_ENABLED"), default=False)

    if not is_enabled:
        logger.info("Automated scraping scheduler is disabled (SCHEDULER_ENABLED=false).")
        return None

    # Parse and validate interval_minutes
    interval_raw = os.getenv("SCHEDULER_INTERVAL_MINUTES", "60").strip()
    try:
        interval_minutes = int(interval_raw)
        if interval_minutes < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid SCHEDULER_INTERVAL_MINUTES: '{interval_raw}'. Must be a positive integer."
        )

    # Validate source_id
    source_id = os.getenv("SCHEDULER_SOURCE_ID", "").strip()
    if not source_id:
        raise ValueError(
            "SCHEDULER_SOURCE_ID is required when SCHEDULER_ENABLED is true."
        )

    # Validate start_url
    start_url = os.getenv("SCHEDULER_START_URL", "").strip()
    if not start_url:
        raise ValueError(
            "SCHEDULER_START_URL is required when SCHEDULER_ENABLED is true."
        )

    # Parse max_pages
    max_pages_raw = os.getenv("SCHEDULER_MAX_PAGES", "3").strip()
    try:
        max_pages = int(max_pages_raw)
        if max_pages < 1:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid SCHEDULER_MAX_PAGES: '{max_pages_raw}'. Must be an integer >= 1."
        )

    # Parse min_request_interval
    interval_req_raw = os.getenv("SCHEDULER_MIN_REQUEST_INTERVAL", "1.0").strip()
    try:
        min_request_interval = float(interval_req_raw)
        if min_request_interval < 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid SCHEDULER_MIN_REQUEST_INTERVAL: '{interval_req_raw}'. Must be a number >= 0."
        )

    provider = os.getenv("SCRAPING_PROVIDER", "direct").strip().lower()

    # Validate provider before starting scheduler
    validated_provider = _validate_provider(provider)
    return start_scheduler(
        source_id=source_id,
        start_url=start_url,
        interval_minutes=interval_minutes,
        max_pages=max_pages,
        min_request_interval=min_request_interval,
        provider=validated_provider,
    )


def stop_scheduler(wait: bool = False) -> None:
    """
    Stop the scheduler safely.

    wait: bool (default: False).
    For web applications (e.g. FastAPI / Uvicorn shutdown), wait=False allows
    the server process to shut down promptly without blocking on the current sleep
    or HTTP cycle, while background threads are cleanly flagged to exit.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=wait)
        logger.info("ScrapeScout scheduler stopped.")

    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Return the current scheduler instance."""
    return _scheduler


def is_scheduler_enabled_in_env() -> bool:
    """Return True when SCHEDULER_ENABLED is explicitly enabled."""
    return parse_bool_env(os.getenv("SCHEDULER_ENABLED"), default=False)


def _parse_time_of_day(time_str: str) -> tuple[int, int]:
    """Parse HH:MM (24-hour) into (hour, minute)."""
    if not isinstance(time_str, str) or ":" not in time_str.strip():
        raise ValueError("time_of_day must be in HH:MM 24-hour format.")
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError("time_of_day must be in HH:MM 24-hour format.")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError("time_of_day must contain valid numeric hours and minutes.") from exc
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        raise ValueError("time_of_day hour must be 0-23 and minute 0-59.")
    return hour, minute


def _resolve_timezone(tz_name: Optional[str]) -> ZoneInfo:
    """Validate and return a ZoneInfo object (defaults to Asia/Kolkata)."""
    name = (tz_name or "Asia/Kolkata").strip() or "Asia/Kolkata"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: '{name}'.") from exc


def build_trigger_for_schedule(schedule: dict):
    """Build an APScheduler trigger from a persisted schedule configuration."""
    frequency = (schedule.get("frequency") or "").strip().lower()
    tz = _resolve_timezone(schedule.get("timezone"))
    time_of_day = schedule.get("time_of_day") or "09:00"

    if frequency == "daily":
        hour, minute = _parse_time_of_day(time_of_day)
        return CronTrigger(hour=hour, minute=minute, timezone=tz)

    if frequency == "weekly":
        hour, minute = _parse_time_of_day(time_of_day)
        weekdays = schedule.get("weekdays")
        if not isinstance(weekdays, list) or not weekdays:
            raise ValueError("Weekly schedules require at least one weekday (0=Mon .. 6=Sun).")
        cleaned_days = []
        for day in weekdays:
            if isinstance(day, bool) or not isinstance(day, int) or not (0 <= day <= 6):
                raise ValueError("Weekdays must be integers between 0 (Monday) and 6 (Sunday).")
            if day not in cleaned_days:
                cleaned_days.append(day)
        day_expr = ",".join(str(d) for d in sorted(cleaned_days))
        return CronTrigger(day_of_week=day_expr, hour=hour, minute=minute, timezone=tz)

    if frequency == "monthly":
        hour, minute = _parse_time_of_day(time_of_day)
        day_of_month = schedule.get("day_of_month")
        if (
            isinstance(day_of_month, bool)
            or not isinstance(day_of_month, int)
            or not (1 <= day_of_month <= 31)
        ):
            raise ValueError("Monthly schedules require day_of_month between 1 and 31.")
        return CronTrigger(day=day_of_month, hour=hour, minute=minute, timezone=tz)

    if frequency == "custom":
        cron_expr = (schedule.get("cron_expression") or "").strip()
        interval_minutes = schedule.get("interval_minutes")
        if cron_expr:
            try:
                return CronTrigger.from_crontab(cron_expr, timezone=tz)
            except Exception as exc:
                raise ValueError(f"Invalid cron_expression '{cron_expr}': {exc}") from exc
        if interval_minutes is not None:
            if (
                isinstance(interval_minutes, bool)
                or not isinstance(interval_minutes, int)
                or interval_minutes < 1
            ):
                raise ValueError("interval_minutes must be a positive integer.")
            return IntervalTrigger(minutes=interval_minutes, timezone=tz)
        raise ValueError("Custom schedules require either cron_expression or interval_minutes.")

    raise ValueError(
        f"Unsupported schedule frequency '{frequency}'. Expected daily, weekly, monthly, or custom."
    )


def calculate_next_run_time(
    schedule: dict,
    reference_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """Calculate the next execution UTC datetime from a schedule configuration."""
    if not schedule.get("is_enabled", True):
        return None
    trigger = build_trigger_for_schedule(schedule)
    tz = _resolve_timezone(schedule.get("timezone"))
    now = reference_time or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)
    next_fire = trigger.get_next_fire_time(None, now)
    if next_fire is None:
        return None
    return next_fire.astimezone(dt_timezone.utc)


def run_with_overlap_guard(fn: Callable, *args, **kwargs):
    """Execute a scheduled job only if no other scraping job is currently running."""
    acquired = _execution_lock.acquire(blocking=False)
    if not acquired:
        logger.warning("Skipping scheduled scraping run because another run is already in progress.")
        return {"skipped": True, "reason": "overlap_prevented"}
    try:
        return fn(*args, **kwargs)
    finally:
        _execution_lock.release()


def ensure_scheduler_started(timezone_name: str = "Asia/Kolkata") -> BackgroundScheduler:
    """Return the running BackgroundScheduler, starting it if needed."""
    global _scheduler
    if _scheduler is None or not _scheduler.running:
        _scheduler = BackgroundScheduler(timezone=timezone_name)
        _scheduler.start()
    return _scheduler


def sync_schedules_to_scheduler(
    schedules: list[dict],
    job_runner: Callable[[str], Any],
) -> Optional[BackgroundScheduler]:
    """
    Synchronize persisted schedule records with APScheduler jobs.
    Only registers live jobs when SCHEDULER_ENABLED is true (or scheduler is already running).
    """
    global _scheduler

    if not is_scheduler_enabled_in_env() and (_scheduler is None or not _scheduler.running):
        logger.info("Scheduler is disabled (SCHEDULER_ENABLED=false); skipping live job registration.")
        return None

    scheduler = ensure_scheduler_started()
    active_job_ids = set()

    for sched in schedules:
        sched_id = str(sched.get("id") or "").strip()
        if not sched_id or not sched.get("is_enabled", True):
            continue
        job_id = f"schedule_{sched_id}"
        try:
            trigger = build_trigger_for_schedule(sched)
        except ValueError as exc:
            logger.error("Skipping invalid schedule %s: %s", sched_id, exc)
            continue

        scheduler.add_job(
            run_with_overlap_guard,
            trigger=trigger,
            id=job_id,
            args=[job_runner, sched_id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        active_job_ids.add(job_id)

    for existing_job in scheduler.get_jobs():
        if existing_job.id.startswith("schedule_") and existing_job.id not in active_job_ids:
            scheduler.remove_job(existing_job.id)

    return scheduler
