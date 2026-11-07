import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction_schema import ExtractedProject
from src.project_validator import validate_project, validate_projects


def sample_project():
    return ExtractedProject(
        title="Build a Web Application",
        description="Create a dashboard using Python.",
        budget="100 - 200",
        currency="USD",
        posted_date="2026-10-20",
        deadline="2026-11-15",
        technologies=["Python", "FastAPI"],
        project_type="Web",
        source_name="Truelancer",
        original_url="https://www.truelancer.com/freelance-project/test-123",
    )


def test_valid_project_passes_validation():
    project = sample_project()

    assert validate_project(project) == []


def test_missing_optional_fields_are_allowed():
    project = sample_project()
    project.description = None
    project.budget = None
    project.currency = None
    project.posted_date = None
    project.deadline = None
    project.project_type = None

    assert validate_project(project) == []


def test_missing_original_url_is_invalid():
    project = sample_project()
    project.original_url = None

    errors = validate_project(project)

    assert "Original URL is required." in errors


def test_blank_original_url_is_invalid():
    project = sample_project()
    project.original_url = "   "

    errors = validate_project(project)

    assert "Original URL is required." in errors


def test_invalid_url_is_detected():
    project = sample_project()
    project.original_url = "not-a-valid-url"

    errors = validate_project(project)

    assert any("Original URL" in error for error in errors)


def test_url_with_credentials_is_invalid():
    project = sample_project()
    project.original_url = "https://user:pass@example.com/project/123"

    errors = validate_project(project)

    assert any("Original URL" in error for error in errors)


def test_invalid_date_is_detected():
    project = sample_project()
    project.posted_date = "2026-15-40"

    errors = validate_project(project)

    assert any("posted_date" in error for error in errors)


def test_invalid_currency_is_detected():
    project = sample_project()
    project.currency = "usd"

    errors = validate_project(project)

    assert any("Currency" in error for error in errors)


def test_invalid_project_type_is_detected():
    project = sample_project()
    project.project_type = "Other"

    errors = validate_project(project)

    assert any("Project type" in error for error in errors)


def test_invalid_technology_value_is_detected():
    project = sample_project()
    project.technologies = ["Python", ""]

    errors = validate_project(project)

    assert any("Technologies" in error for error in errors)


def test_validate_multiple_projects():
    valid_project = sample_project()

    invalid_project = sample_project()
    invalid_project.title = ""

    results = validate_projects([valid_project, invalid_project])

    assert len(results) == 1
    assert 1 in results
    assert "Title is required." in results[1]