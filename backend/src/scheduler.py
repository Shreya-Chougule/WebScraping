
"""
ScrapeScout scheduler.

The scheduler does not start automatically on import.
Call start_scheduler() explicitly when scheduling is required.
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.pipeline import run_truelancer_pipeline


logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def scheduled_truelancer_job(
    source_id: str,
    start_url: str,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
):
    """Execute one scheduled Truelancer pipeline run."""

    try:
        logger.info("Starting scheduled Truelancer pipeline.")

        result = run_truelancer_pipeline(
            source_id=source_id,
            start_url=start_url,
            max_pages=max_pages,
            min_request_interval=min_request_interval,
        )

        logger.info(
            "Scheduled pipeline finished with status: %s",
            result.get("status"),
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
) -> BackgroundScheduler:
    """
    Start the background scheduler and register one interval job.

    Repeated calls reuse the existing scheduler and job.
    """

    global _scheduler

    if not source_id or not isinstance(source_id, str):
        raise ValueError("A valid source_id is required.")

    if not start_url or not isinstance(start_url, str):
        raise ValueError("A valid start_url is required.")

    if (
        not isinstance(interval_minutes, int)
        or isinstance(interval_minutes, bool)
        or interval_minutes < 1
    ):
        raise ValueError("interval_minutes must be a positive integer.")

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    if min_request_interval < 0:
        raise ValueError("min_request_interval cannot be negative.")

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


def stop_scheduler(wait: bool = True) -> None:
    """Stop the scheduler safely."""

    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=wait)
        logger.info("ScrapeScout scheduler stopped.")

    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Return the current scheduler instance."""

    return _scheduler
