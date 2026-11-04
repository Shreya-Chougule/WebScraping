
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


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
    pricing_type: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the project into a dictionary for export."""
        return asdict(self)


def save_projects_json(
    projects: list[ExtractedProject],
    output_path: str,
) -> None:
    """Save extracted projects as a JSON array."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = [project.to_dict() for project in projects]

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def save_projects_csv(
    projects: list[ExtractedProject],
    output_path: str,
) -> None:
    """Save extracted projects as a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(ExtractedProject.__dataclass_fields__.keys())

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for project in projects:
            row = project.to_dict()
            row["technologies"] = ", ".join(row["technologies"])
            writer.writerow(row)
