import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from src.extraction_schema import ExtractedProject


def clean_text(value: str | None) -> str | None:
    """Remove HTML markup, decode entities, and normalize whitespace."""
    if not isinstance(value, str):
        return None

    text = BeautifulSoup(unescape(value), "html.parser").get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.!?])(?=[A-Z])", r"\1 ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def infer_truelancer_project_type(
    title: str,
    description: str | None,
    technologies: list[str],
) -> str | None:
    """Infer project type conservatively, avoiding incidental mentions."""

    title_text = title.lower()
    description_text = (description or "").lower()

    web_patterns = (
        r"\bweb\s+app(?:lication)?\b",
        r"\bweb\s+development\b",
        r"\bwebsite\s+(?:development|design|redesign|creation)\b",
        r"\bfrontend\s+development\b",
        r"\bfront-end\s+development\b",
        r"\bweb\s+portal\b",
        r"\bwebsite\s+developer\b",
        r"\bweb\s+developer\b",
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

    def matches(patterns: tuple[str, ...], value: str) -> bool:
        return any(re.search(pattern, value) for pattern in patterns)

    # Strong evidence in the project title takes priority.
    title_web = matches(web_patterns, title_text)
    title_mobile = matches(mobile_patterns, title_text)
    title_software = matches(software_patterns, title_text)

    if title_web and title_mobile:
        return "Both"

    if title_web:
        return "Web"

    if title_mobile:
        return "Mobile App"

    if title_software:
        return "Software"

    # Description-only classification requires stronger wording:
    # the project must explicitly request development or creation.
    web_request_patterns = (
        r"\b(?:develop|build|create|design)\b.{0,80}\b(?:website|web\s+app|web\s+application|web\s+portal)\b",
        r"\b(?:website|web\s+app|web\s+application|web\s+portal)\b.{0,80}\b(?:develop|build|create|redesign)\b",
    )

    mobile_request_patterns = (
        r"\b(?:develop|build|create)\b.{0,80}\b(?:mobile|android|ios|iphone)\s+app\b",
        r"\b(?:mobile|android|ios|iphone)\s+app\b.{0,80}\b(?:develop|build|create)\b",
    )

    software_request_patterns = (
        r"\b(?:develop|build|create)\b.{0,80}\b(?:desktop|windows)\s+(?:application|software)\b",
        r"\b(?:desktop|windows)\s+(?:application|software)\b.{0,80}\b(?:develop|build|create)\b",
    )

    has_web = matches(web_request_patterns, description_text)
    has_mobile = matches(mobile_request_patterns, description_text)
    has_software = matches(software_request_patterns, description_text)

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

    path = parts.path.rstrip("/")

    return urlunsplit(
        ("https", hostname, path, "", "")
    ).lower()


def parse_truelancer_html(html: str) -> list[ExtractedProject]:
    """Extract unique projects from locally saved Truelancer HTML."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if script is None or not script.string:
        raise ValueError(
            "Truelancer embedded project data was not found."
        )

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

        title = clean_text(record.get("title"))

        if title is None:
            continue

        description = clean_text(record.get("description"))

        budget_value = record.get("budget")

        budget = (
            str(budget_value).strip()
            if budget_value is not None and str(budget_value).strip()
            else None
        )

        currency = clean_text(record.get("currency"))

        if currency:
            currency = currency.upper()

        raw_date = record.get("created_at")
        posted_date = None

        if isinstance(raw_date, str) and len(raw_date) >= 10:
            date_candidate = raw_date[:10]

            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_candidate):
                posted_date = date_candidate

        skills: Any = record.get("skills")
        technologies: list[str] = []

        if isinstance(skills, list):
            for skill in skills:
                if not isinstance(skill, dict):
                    continue

                name = clean_text(
                    skill.get("tagName") or skill.get("name")
                )

                if name:
                    technologies.append(name)

        technologies = list(dict.fromkeys(technologies))

        raw_url = record.get("link")

        original_url = (
            raw_url.strip()
            if isinstance(raw_url, str) and raw_url.strip()
            else None
        )

        canonical_url = canonicalize_url(original_url)

        if original_url and canonical_url is None:
            original_url = None

        if canonical_url and canonical_url in seen_urls:
            continue

        if canonical_url:
            seen_urls.add(canonical_url)

        pricing_type = clean_text(record.get("jobTypeName"))

        country = record.get("countryObj")
        location = None
        if isinstance(country, dict):
            location = clean_text(country.get("name"))

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
                currency=currency,
                posted_date=posted_date,
                deadline=None,
                technologies=technologies,
                project_type=project_type,
                source_name="Truelancer",
                original_url=original_url,
                pricing_type=pricing_type,
                location=location,
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