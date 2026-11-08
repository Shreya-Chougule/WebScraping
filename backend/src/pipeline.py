
"""
ScrapeScout end-to-end Truelancer pipeline.

Coordinates scraping, API submission, and scraping-run logging.
Importing this module does not start scraping or scheduling.
"""

import json
from typing import Optional

from src.extraction_schema import ExtractedProject
from src.scraper import (
    SCRAPING_RUNS_ENDPOINT,
    create_scraping_run,
    scrape_truelancer_pages,
    send_projects_to_api,
    update_scraping_run,
)


def run_truelancer_pipeline(
    source_id: str,
    start_url: str,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
    api_endpoint: str = SCRAPING_RUNS_ENDPOINT,
    fetcher=None,
    sleep_fn=None,
    scraper=None,
    submitter=None,
    run_creator=None,
    run_updater=None,
) -> dict:
    """Execute the complete Truelancer scraping and submission workflow."""

    if not source_id or not isinstance(source_id, str):
        raise ValueError("A valid source_id is required.")

    if not start_url or not isinstance(start_url, str):
        raise ValueError("A valid start_url is required.")

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    if min_request_interval < 0:
        raise ValueError("min_request_interval cannot be negative.")

    create_run = run_creator or create_scraping_run
    update_run = run_updater or update_scraping_run
    scrape = scraper or scrape_truelancer_pages
    submit = submitter or send_projects_to_api

    run_id = create_run(
        source_id=source_id,
        api_endpoint=api_endpoint,
    )

    projects = []
    records_found = 0

    try:
        projects = scrape(
            start_url=start_url,
            max_pages=max_pages,
            min_request_interval=min_request_interval,
            fetcher=fetcher,
            sleep_fn=sleep_fn,
        )

        if not isinstance(projects, list):
            raise ValueError("Scraper did not return a project list.")

        records_found = len(projects)

        submission_results = submit(projects)

        if not isinstance(submission_results, dict):
            raise ValueError("Submission function returned an invalid result.")

        if "failed" not in submission_results:
            raise ValueError(
                "Submission results are missing the failed count."
            )

        failed_count = submission_results["failed"]

        if (
            not isinstance(failed_count, int)
            or isinstance(failed_count, bool)
            or failed_count < 0
        ):
            raise ValueError("Submission failed count is invalid.")

        status = "FAILED" if failed_count > 0 else "SUCCESS"

        error_log: Optional[str] = None

        if status == "FAILED":
            error_log = (
                "One or more project submissions failed. "
                "Submission summary: "
                + json.dumps(submission_results, default=str)
            )[:5000]

        update_run(
            run_id=run_id,
            status=status,
            records_found=records_found,
            error_log=error_log,
            api_endpoint=api_endpoint,
        )

        result = {
            "run_id": run_id,
            "status": status,
            "records_found": records_found,
            "submission": submission_results,
        }

        print(f"[PIPELINE] Completed: {result}")

        return result

    except Exception as exc:
        try:
            update_run(
                run_id=run_id,
                status="FAILED",
                records_found=records_found,
                error_log=str(exc)[:5000],
                api_endpoint=api_endpoint,
            )
        except Exception as logging_error:
            print(
                "[ERROR] Could not update failed pipeline run: "
                f"{logging_error}"
            )

        raise
