import re
from datetime import datetime
from urllib.parse import urlsplit

from src.extraction_schema import ExtractedProject


VALID_PROJECT_TYPES = {
    "Web",
    "App",
    "Mobile App",  # Accepted for backward compatibility
    "Software",
    "Both",
}

DATE_FORMAT = "%Y-%m-%d"


def is_valid_date(value: str) -> bool:
    """Check whether a date follows YYYY-MM-DD and is a real date."""
    try:
        return datetime.strptime(value, DATE_FORMAT).strftime(
            DATE_FORMAT
        ) == value
    except ValueError:
        return False


def is_valid_url(value: str) -> bool:
    """Check whether a URL is an absolute HTTP or HTTPS URL."""
    if not isinstance(value, str) or not value.strip():
        return False

    try:
        parts = urlsplit(value)

        if parts.scheme == "https":
            valid_port = parts.port in (None, 443)
        elif parts.scheme == "http":
            valid_port = parts.port in (None, 80)
        else:
            valid_port = False

        return (
            valid_port
            and bool(parts.netloc)
            and bool(parts.hostname)
            and parts.username is None
            and parts.password is None
            and not any(char.isspace() for char in value)
        )

    except ValueError:
        return False


def validate_project(project: ExtractedProject) -> list[str]:
    """
    Validate an extracted project without modifying its data.

    Returns a list of validation errors.
    An empty list means the project passed validation.
    """
    errors = []

    # Required fields
    if not isinstance(project.title, str) or not project.title.strip():
        errors.append("Title is required.")

    if (
        not isinstance(project.source_name, str)
        or not project.source_name.strip()
    ):
        errors.append("Source name is required.")

    # Original URL is required because the database column is NOT NULL.
    if (
        not isinstance(project.original_url, str)
        or not project.original_url.strip()
    ):
        errors.append("Original URL is required.")

    elif not is_valid_url(project.original_url):
        errors.append(
            "Original URL must be a valid HTTP or HTTPS URL."
        )

    # Optional date fields
    for field_name in ("posted_date", "deadline"):
        value = getattr(project, field_name)

        if value is not None:
            if not isinstance(value, str) or not is_valid_date(value):
                errors.append(
                    f"{field_name} must use YYYY-MM-DD format."
                )

    # Optional currency: three uppercase letters.
    if project.currency is not None:
        if (
            not isinstance(project.currency, str)
            or not re.fullmatch(r"[A-Z]{3}", project.currency)
        ):
            errors.append(
                "Currency must be a three-letter uppercase code."
            )

    # Optional project type
    if project.project_type is not None:
        if project.project_type not in VALID_PROJECT_TYPES:
            errors.append("Project type is not a supported value.")

    # Technologies must be a list of non-empty strings.
    if not isinstance(project.technologies, list):
        errors.append("Technologies must be a list.")

    elif any(
        not isinstance(item, str) or not item.strip()
        for item in project.technologies
    ):
        errors.append(
            "Technologies must contain only non-empty strings."
        )

    # Optional text fields
    for field_name in ("description", "budget", "pricing_type"):
        value = getattr(project, field_name)

        if value is not None and not isinstance(value, str):
            errors.append(f"{field_name} must be text or None.")

    return errors


def validate_projects(
    projects: list[ExtractedProject],
) -> dict[int, list[str]]:
    """
    Validate multiple projects.

    Returns a dictionary containing only invalid records.
    Keys are zero-based project indexes.
    """
    invalid_projects = {}

    for index, project in enumerate(projects):
        errors = validate_project(project)

        if errors:
            invalid_projects[index] = errors

    return invalid_projects