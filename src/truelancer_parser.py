
import json
from html import unescape
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from src.extraction_schema import ExtractedProject


def parse_truelancer_html(html: str) -> list[ExtractedProject]:
    """Extract projects from a locally saved Truelancer HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if script is None or not script.string:
        raise ValueError("Truelancer embedded project data was not found.")

    try:
        data = json.loads(script.string)
        records = data["props"]["pageProps"]["data"]["projects"]["data"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(
            "Unexpected Truelancer project data structure."
        ) from exc

    projects = []

    for record in records:
        title = record.get("title")
        if not isinstance(title, str) or not title.strip():
            continue

        description = record.get("description")
        if isinstance(description, str):
            description = unescape(description).strip() or None
        else:
            description = None

        budget_value = record.get("budget")
        currency = record.get("currency")

        if budget_value is not None:
            budget = (
                f"{currency} {budget_value}"
                if currency
                else str(budget_value)
            )
        else:
            budget = None

        raw_date = record.get("created_at")
        posted_date = (
            raw_date[:10]
            if isinstance(raw_date, str) and len(raw_date) >= 10
            else None
        )

        skills: Any = record.get("skills")
        technologies = []

        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    name = skill.get("tagName") or skill.get("name")
                    if isinstance(name, str) and name.strip():
                        technologies.append(name.strip())

        technologies = list(dict.fromkeys(technologies))

        original_url = record.get("link")
        if not (
            isinstance(original_url, str)
            and original_url.startswith(
                (
                    "https://www.truelancer.com/freelance-project/",
                    "https://truelancer.com/freelance-project/",
                )
            )
        ):
            original_url = None

        pricing_type = record.get("jobTypeName")
        if isinstance(pricing_type, str):
            pricing_type = pricing_type.strip() or None
        else:
            pricing_type = None

        projects.append(
            ExtractedProject(
                title=title.strip(),
                description=description,
                budget=budget,
                posted_date=posted_date,
                deadline=None,
                technologies=technologies,
                project_type=None,
                source_name="Truelancer",
                original_url=original_url,
                pricing_type=pricing_type,
            )
        )

    return projects


def parse_truelancer_file(
    file_path: str = "test_data/truelancer_listings.html",
) -> list[ExtractedProject]:
    """Parse a saved HTML file without making network requests."""
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="replace")
    return parse_truelancer_html(html)