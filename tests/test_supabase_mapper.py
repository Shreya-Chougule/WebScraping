
from src.extraction_schema import ExtractedProject
from src.supabase_mapper import (
    map_project_to_supabase,
    convert_date,
    normalize_project_type,
)


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
        pricing_type="Fixed Price",
    )


def test_convert_date():
    assert convert_date("2026-10-20") == "2026-10-20T00:00:00"


def test_convert_missing_date():
    assert convert_date(None) is None


def test_normalize_mobile_app_project_type():
    assert normalize_project_type("Mobile App") == "Mobile"


def test_normalize_app_project_type():
    assert normalize_project_type("App") == "Mobile"


def test_normalize_mobile_project_type():
    assert normalize_project_type("Mobile") == "Mobile"


def test_normalize_other_project_types():
    assert normalize_project_type("Web") == "Web"
    assert normalize_project_type("Both") == "Both"


def test_normalize_software_project_type():
    assert normalize_project_type("Software") == "Unspecified"


def test_normalize_missing_project_type():
    assert normalize_project_type(None) == "Unspecified"


def test_normalize_unspecified_project_type():
    assert normalize_project_type("Not specified") == "Unspecified"
    assert normalize_project_type("Unspecified") == "Unspecified"


def test_normalize_unknown_project_type():
    assert normalize_project_type("Something else") == "Unspecified"


def test_normalize_project_type_is_case_insensitive():
    assert normalize_project_type("mobile app") == "Mobile"
    assert normalize_project_type("WEB") == "Web"
    assert normalize_project_type("both") == "Both"


def test_map_project_to_supabase():
    project = sample_project()

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["title"] == "Build a Web Application"
    assert result["currency"] == "USD"
    assert result["required_technologies"] == ["Python", "FastAPI"]
    assert result["source_id"] == "2f85be5b-f177-432b-92c9-33ca2707139c"
    assert result["posted_date"] == "2026-10-20T00:00:00"
    assert result["deadline"] == "2026-11-15T00:00:00"
    assert result["project_type"] == "Web"


def test_mapper_normalizes_mobile_app_before_database_submission():
    project = sample_project()
    project.project_type = "Mobile App"

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["project_type"] == "Mobile"


def test_mapper_normalizes_app_before_database_submission():
    project = sample_project()
    project.project_type = "App"

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["project_type"] == "Mobile"


def test_mapper_normalizes_software_before_database_submission():
    project = sample_project()
    project.project_type = "Software"

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["project_type"] == "Unspecified"


def test_mapper_converts_unspecified_project_type_to_database_value():
    project = sample_project()
    project.project_type = "Not specified"

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["project_type"] == "Unspecified"


def test_mapper_handles_missing_project_type():
    project = sample_project()
    project.project_type = None

    result = map_project_to_supabase(
        project,
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert result["project_type"] == "Unspecified"


def test_mapper_excludes_pricing_type():
    result = map_project_to_supabase(
        sample_project(),
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert "pricing_type" not in result


def test_mapper_uses_database_field_names():
    result = map_project_to_supabase(
        sample_project(),
        "2f85be5b-f177-432b-92c9-33ca2707139c",
    )

    assert "technologies" not in result
    assert "required_technologies" in result
