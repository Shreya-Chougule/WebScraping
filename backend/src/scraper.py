
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

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

NOT_SPECIFIED = "Not specified"


def clean_text(value: Optional[str]) -> Optional[str]:
    """Normalize whitespace and return None when text is missing."""
    if not value:
        return None

    cleaned = " ".join(value.split())
    return cleaned or None


def infer_project_type(
    title: str,
    description: Optional[str] = None,
    technologies: Optional[list[str]] = None,
) -> str:
    """
    Infer whether a project is for a web app, mobile app, or both.

    Returns 'Not specified' when there is insufficient evidence.
    """
    text = " ".join(
        part for part in [title, description or "", " ".join(technologies or [])]
        if part
    ).lower()

    web_terms = (
        "website",
        "web app",
        "web application",
        "web development",
        "frontend",
        "front-end",
        "browser-based",
    )

    mobile_terms = (
        "mobile app",
        "mobile application",
        "android app",
        "ios app",
        "iphone app",
        "flutter",
        "react native",
    )

    has_web = any(term in text for term in web_terms)
    has_mobile = any(term in text for term in mobile_terms)

    if has_web and has_mobile:
        return "Both"
    if has_web:
        return "Web"
    if has_mobile:
        return "Mobile App"

    return NOT_SPECIFIED


def resolve_project_url(
    base_url: str,
    href: Optional[str],
) -> str:
    """
    Resolve a relative project link.

    Do not silently treat the listing page as a verified project URL.
    """
    if not href:
        return NOT_SPECIFIED

    resolved_url = urljoin(base_url, href.strip())
    parsed = urlparse(resolved_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return NOT_SPECIFIED

    return resolved_url


def parse_project_cards(
    html: str,
    source_name: str,
    base_url: str,
    card_selector: str,
    title_selector: str,
    description_selector: Optional[str] = None,
    budget_selector: Optional[str] = None,
    technologies_selector: Optional[str] = None,
    posted_date_selector: Optional[str] = None,
    deadline_selector: Optional[str] = None,
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

        posted_date_element = (
            card.select_one(posted_date_selector)
            if posted_date_selector
            else None
        )

        deadline_element = (
            card.select_one(deadline_selector)
            if deadline_selector
            else None
        )

        description = (
            clean_text(description_element.get_text(" ", strip=True))
            if description_element
            else None
        )

        budget = (
            clean_text(budget_element.get_text(" ", strip=True))
            if budget_element
            else None
        )

        posted_date = (
            clean_text(
                posted_date_element.get("datetime")
                or posted_date_element.get_text(" ", strip=True)
            )
            if posted_date_element
            else None
        )

        deadline = (
            clean_text(
                deadline_element.get("datetime")
                or deadline_element.get_text(" ", strip=True)
            )
            if deadline_element
            else None
        )

        # Find the project link, if present.
        link_element = (
            title_element
            if title_element.name == "a"
            else title_element.find("a")
        )

        href = link_element.get("href") if link_element else None
        original_url = resolve_project_url(base_url, href)

        # Extract technologies and remove duplicates case-insensitively.
        technology_elements = (
            card.select(technologies_selector)
            if technologies_selector
            else []
        )

        technologies = []
        seen_technologies = set()

        for element in technology_elements:
            technology = clean_text(element.get_text(" ", strip=True))

            if technology and technology.casefold() not in seen_technologies:
                technologies.append(technology)
                seen_technologies.add(technology.casefold())

        project_type = infer_project_type(
            title=title,
            description=description,
            technologies=technologies,
        )

        project = ExtractedProject(
            title=title,
            description=description or NOT_SPECIFIED,
            budget=budget or NOT_SPECIFIED,
            posted_date=posted_date or NOT_SPECIFIED,
            deadline=deadline or NOT_SPECIFIED,
            technologies=technologies,
            project_type=project_type,
            source_name=source_name or NOT_SPECIFIED,
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

        # Avoid submitting records without a verified project URL.
        if project.original_url == NOT_SPECIFIED:
            print(f"[SKIPPED] Missing project URL: {project.title}")
            continue

        try:
            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=15,
            )

            if response.status_code in (200, 201):
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
