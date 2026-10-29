
import json
from html import unescape
from pathlib import Path
from typing import Optional, Any

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

        # Description: preserve the supplied text; use None if missing.
        description = record.get("description")
        if isinstance(description, str):
            description = unescape(description).strip() or None
        else:
            description = None

        # Budget: retain the source currency and amount.
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

        # Keep the date in ISO YYYY-MM-DD format when available.
        raw_date = record.get("created_at")
        posted_date = (
            raw_date[:10]
            if isinstance(raw_date, str) and len(raw_date) >= 10
            else None
        )

        # Extract skills without duplicates.
        skills: Any = record.get("skills")
        technologies = []

        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    name = skill.get("tagName") or skill.get("name")
                    if isinstance(name, str) and name.strip():
                        technologies.append(name.strip())

        technologies = list(dict.fromkeys(technologies))

        # Accept only project links on Truelancer's domain.
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
            )
        )

    return projects


def parse_truelancer_file(
    file_path: str = "test_data/truelancer_listings.html",
) -> list[ExtractedProject]:
    """Parse a saved HTML file without making network requests."""
    path = Path(file_path)

    html = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    return parse_truelancer_html(html)

