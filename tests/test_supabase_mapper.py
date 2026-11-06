
from src.extraction_schema import ExtractedProject
from src.supabase_mapper import map_project_to_supabase, convert_date


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
