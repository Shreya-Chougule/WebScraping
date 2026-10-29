import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from src.extraction_schema import ExtractedProject


def infer_truelancer_project_type(
    title: str,
    description: str | None,
    technologies: list[str],
) -> str | None:
    """Classify only when the title or description gives clear evidence.

    Technologies are deliberately excluded from classification because a
    skill such as Android development does not prove the project itself
    is a mobile app.
    """
    text = f"{title} {description or ''}".lower()

    web_patterns = (
        r"\bweb\s+app(?:lication)?\b",
        r"\bweb\s+development\b",
        r"\bwebsite\s+(?:development|design|redesign|creation)\b",
        r"\bfrontend\s+development\b",
        r"\bfront-end\s+development\b",
        r"\bweb\s+portal\b",
    )

    mobile_patterns = (
        r"\bmobile\s+app(?:lication)?\b",
        r"\bandroid\s+app(?:lication)?\b",
        r"\bios\s+app(?:lication)?\b",
        r"\biphone\s+app(?:lication)?\b",
        r"\bmobile\s+app\s+development\b",
    )

    software_patterns = (
        r"\bdesktop\s+application\b",
        r"\bdesktop\s+software\b",
        r"\bwindows\s+application\b",
        r"\bsoftware\s+development\b",
        r"\bsoftware\s+application\b",
    )

    has_web = any(re.search(pattern, text) for pattern in web_patterns)
    has_mobile = any(
        re.search(pattern, text) for pattern in mobile_patterns
    )
    has_software = any(
        re.search(pattern, text) for pattern in software_patterns
    )

    if has_web and has_mobile:
        return "Both"
    if has_web:
        return "Web"
    if has_mobile:
        return "Mobile App"
    if has_software:
        return "Software"

    return None


def canonicalize_url(url: str | None) -> str | None:
    """Normalize a valid Truelancer listing URL for duplicate detection."""
    if not isinstance(url, str) or not url.strip():
        return None

    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None

    hostname = (parts.hostname or "").lower()

    if hostname not in {"truelancer.com", "www.truelancer.com"}:
        return None

    if not parts.path.startswith("/freelance-project/"):
        return None

    # Query strings and fragments do not identify different listings.
    path = parts.path.rstrip("/")
    return urlunsplit(("https", hostname, path, "", "")).lower()


def parse_truelancer_html(html: str) -> list[ExtractedProject]:
    """Extract unique projects from locally saved Truelancer HTML."""
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

    projects: list[ExtractedProject] = []
    seen_urls: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        title = record.get("title")
        if not isinstance(title, str) or not title.strip():
            continue

        title = title.strip()

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
        technologies: list[str] = []

        if isinstance(skills, list):
            for skill in skills:
                if not isinstance(skill, dict):
                    continue

                name = skill.get("tagName") or skill.get("name")
                if isinstance(name, str) and name.strip():
                    technologies.append(name.strip())

        technologies = list(dict.fromkeys(technologies))

        raw_url = record.get("link")
        original_url = (
            raw_url.strip()
            if isinstance(raw_url, str)
            else None
        )

        canonical_url = canonicalize_url(original_url)

        if original_url and canonical_url is None:
            original_url = None

        if canonical_url and canonical_url in seen_urls:
            continue

        if canonical_url:
            seen_urls.add(canonical_url)

        pricing_type = record.get("jobTypeName")
        if isinstance(pricing_type, str):
            pricing_type = pricing_type.strip() or None
        else:
            pricing_type = None

        project_type = infer_truelancer_project_type(
            title=title,
            description=description,
            technologies=technologies,
        )

        projects.append(
            ExtractedProject(
                title=title,
                description=description,
                budget=budget,
                posted_date=posted_date,
                deadline=None,
                technologies=technologies,
                project_type=project_type,
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