
from datetime import datetime

from src.extraction_schema import ExtractedProject


NOT_SPECIFIED = "Not specified"


def convert_date(value: str | None) -> str | None:
    """Convert YYYY-MM-DD into an ISO datetime string."""
    if not value or value.strip().casefold() == NOT_SPECIFIED.casefold():
        return None

    parsed_date = datetime.strptime(value, "%Y-%m-%d")
    return parsed_date.isoformat()


def map_project_to_supabase(
    project: ExtractedProject,
    source_id: str,
) -> dict:
    """
    Map an extracted project to the Supabase projects table format.

    The source_id must be resolved from the Supabase sources table.
    """
    return {
        "title": project.title,
        "description": (
            None if project.description == NOT_SPECIFIED
            else project.description
        ),
        "budget": (
            None if project.budget == NOT_SPECIFIED
            else project.budget
        ),
        "currency": project.currency,
        "posted_date": convert_date(project.posted_date),
        "deadline": convert_date(project.deadline),
        "required_technologies": project.technologies,
        "project_type": (
            None if project.project_type == NOT_SPECIFIED
            else project.project_type
        ),
        "source_id": source_id,
        "original_url": project.original_url,
    }
