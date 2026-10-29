
from dataclasses import dataclass, asdict
from typing import Optional
import json
import csv


@dataclass
class ExtractedProject:
    title: str
    description: Optional[str]
    budget: Optional[str]
    posted_date: Optional[str]
    deadline: Optional[str]
    technologies: list[str]
    project_type: Optional[str]
    source_name: str
    original_url: str

    def to_dict(self) -> dict:
        return asdict(self)


def save_projects_json(
    projects: list[ExtractedProject],
    output_path: str,
) -> None:
    """Save extracted projects to a UTF-8 JSON file."""
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            [project.to_dict() for project in projects],
            file,
            ensure_ascii=False,
            indent=2,
        )


def save_projects_csv(
    projects: list[ExtractedProject],
    output_path: str,
) -> None:
    """Save extracted projects to a UTF-8 CSV file."""
    fieldnames = [
        "title",
        "description",
        "budget",
        "posted_date",
        "deadline",
        "technologies",
        "project_type",
        "source_name",
        "original_url",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for project in projects:
            row = project.to_dict()
            row["technologies"] = ", ".join(project.technologies)
            writer.writerow(row)
