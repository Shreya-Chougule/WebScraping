
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction_schema import (
    ExtractedProject,
    save_projects_csv,
    save_projects_json,
)


def sample_project():
    return ExtractedProject(
        title="Test Web Application",
        description="Build a demo application",
        budget="$100 - $200",
        posted_date="2026-10-20",
        deadline="2026-11-15",
        technologies=["Python", "FastAPI"],
        project_type="Web",
        source_name="Local HTML Test",
        original_url="https://example.com/project/123",
    )


def test_project_to_dict():
    project = sample_project()
    data = project.to_dict()

    assert data["title"] == "Test Web Application"
    assert data["technologies"] == ["Python", "FastAPI"]
    assert data["project_type"] == "Web"


def test_save_projects_json(tmp_path):
    project = sample_project()
    output_file = tmp_path / "projects.json"

    save_projects_json([project], str(output_file))

    assert output_file.exists()

    import json
    data = json.loads(output_file.read_text(encoding="utf-8"))

    assert len(data) == 1
    assert data[0]["title"] == "Test Web Application"
    assert data[0]["technologies"] == ["Python", "FastAPI"]


def test_save_projects_csv(tmp_path):
    import csv

    project = sample_project()
    output_file = tmp_path / "projects.csv"

    save_projects_csv([project], str(output_file))

    assert output_file.exists()

    with output_file.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["title"] == "Test Web Application"
    assert rows[0]["technologies"] == "Python, FastAPI"
