
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
Path("output").mkdir(exist_ok=True)
from src.extraction_schema import (
    ExtractedProject,
    save_projects_json,
    save_projects_csv,
)

sample_projects = [
    ExtractedProject(
        title="Example Web Development Project",
        description="Build a responsive website using React and Python.",
        budget="500-1000 USD",
        posted_date="2026-10-28",
        deadline=None,
        technologies=["React", "Python"],
        project_type="Web",
        source_name="Test Fixture",
        original_url="https://example.com/project/123",
    )
]

save_projects_json(sample_projects, "output/test_projects_test.json")
save_projects_csv(sample_projects, "output/test_projects_test.csv")

print("JSON and CSV export tests completed.")
