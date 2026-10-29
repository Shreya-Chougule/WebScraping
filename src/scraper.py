
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.extraction_schema import (
    ExtractedProject,
    save_projects_csv,
    save_projects_json,
)

API_ENDPOINT = "http://127.0.0.1:8000/projects"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def clean_text(value: Optional[str]) -> Optional[str]:
    """Normalize text and return None when it is missing."""
    if not value:
        return None

    cleaned = " ".join(value.split())
    return cleaned or None


def parse_project_cards(
    html: str,
    source_name: str,
    base_url: str,
    card_selector: str,
    title_selector: str,
    description_selector: Optional[str] = None,
    budget_selector: Optional[str] = None,
    technologies_selector: Optional[str] = None,
) -> list[ExtractedProject]:
    """Extract project details from HTML using configured CSS selectors."""
    soup = BeautifulSoup(html, "html.parser")
    projects = []

    for card in soup.select(card_selector):
        title_element = card.select_one(title_selector)

        if not title_element:
            continue

        title = clean_text(title_element.get_text(" ", strip=True))

        if not title:
            continue

        description_element = (
            card.select_one(description_selector)
            if description_selector
            else None
        )

        budget_element = (
            card.select_one(budget_selector)
            if budget_selector
            else None
        )

        # Extract the project URL from the title link when available.
        link_element = (
            title_element
            if title_element.name == "a"
            else title_element.find("a")
        )

        href = link_element.get("href") if link_element else None

        original_url = (
            requests.compat.urljoin(base_url, href)
            if href
            else base_url
        )

        # Extract technologies, if the source provides them.
        technology_elements = (
            card.select(technologies_selector)
            if technologies_selector
            else []
        )

        technologies = []

        for element in technology_elements:
            technology = clean_text(element.get_text(" ", strip=True))

            if technology:
                technologies.append(technology)

        project = ExtractedProject(
            title=title,
            description=(
                clean_text(description_element.get_text(" ", strip=True))
                if description_element
                else None
            ),
            budget=(
                clean_text(budget_element.get_text(" ", strip=True))
                if budget_element
                else None
            ),
            posted_date=None,
            deadline=None,
            technologies=technologies,
            project_type="Software",
            source_name=source_name,
            original_url=original_url,
        )

        projects.append(project)

    return projects


def export_projects(projects: list[ExtractedProject]) -> None:
    """Save extracted project records to JSON and CSV."""
    json_path = OUTPUT_DIR / "projects.json"
    csv_path = OUTPUT_DIR / "projects.csv"

    save_projects_json(projects, str(json_path))
    save_projects_csv(projects, str(csv_path))

    print(f"Exported {len(projects)} projects.")
    print(f"JSON file: {json_path}")
    print(f"CSV file: {csv_path}")


def send_projects_to_api(
    projects: list[ExtractedProject],
    api_endpoint: str = API_ENDPOINT,
) -> None:
    """
    Send projects to the existing API.

    Only fields supported by the current ProjectCreate schema are sent.
    """
    for project in projects:
        payload = {
            "title": project.title,
            "original_url": project.original_url,
            "description": project.description,
        }

        try:
            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=15,
            )

            if response.status_code == 201:
                print(f"[SUCCESS] Inserted: {project.title}")

            elif response.status_code == 400:
                print(f"[SKIPPED] Request rejected: {project.title}")
                print(response.text)

            else:
                print(
                    f"[ERROR] HTTP {response.status_code}: "
                    f"{project.title} - {response.text}"
                )

        except requests.RequestException as exc:
            print(f"[ERROR] API connection failed: {exc}")


if __name__ == "__main__":
    print("ScrapeScout extraction module is ready.")
    print("Configure selectors for an approved source before fetching live pages.")
