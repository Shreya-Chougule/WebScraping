
import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from src.classifier import ProjectClassifier
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
    """
    Infer project type from explicit title, description, and skill evidence.

    Supported values: Web, App, Software, Both, or None.
    """

    title_text = title.lower()
    description_text = (description or "").lower()
    technology_text = " ".join(technologies or []).lower()

    def matches(patterns: tuple[str, ...], value: str) -> bool:
        return any(re.search(pattern, value) for pattern in patterns)

    web_title_patterns = (
        r"\bweb\s+app(?:lication)?\b",
        r"\bweb\s+development\b",
        r"\bwebsite\s+(?:development|design|redesign|creation)\b",
        r"\bfrontend\s+development\b",
        r"\bfront-end\s+development\b",
        r"\bweb\s+portal\b",
        r"\bwebsite\s+developer\b",
        r"\bweb\s+developer\b",
        r"\bweb\s+designer\b",
    )

    app_title_patterns = (
        r"\bmobile\s+app(?:lication)?\b",
        r"\bandroid\s+app(?:lication)?\b",
        r"\bios\s+app(?:lication)?\b",
        r"\biphone\s+app(?:lication)?\b",
        r"\bflutter\s+app(?:lication)?\b",
        r"\breact\s+native\s+app(?:lication)?\b",
    )

    software_title_patterns = (
        r"\bdesktop\s+application\b",
        r"\bdesktop\s+software\b",
        r"\bwindows\s+application\b",
        r"\bsoftware\s+development\b",
        r"\bsoftware\s+application\b",
    )

    web_skill_patterns = (
        r"\bweb\s+development\b",
        r"\bweb\s+design\b",
        r"\bwebsite\s+development\b",
        r"\bwebsite\s+design\b",
        r"\bfrontend\s+development\b",
        r"\bfront-end\s+development\b",
        r"\bweb\s+application\s+development\b",
        r"\bweb\s+app\s+development\b",
        r"\breact(?:\.js)?\b(?!\s*native)",
        r"\bangular(?:\.js)?\b",
        r"\bvue(?:\.js)?\b",
        r"\bwordpress\b",
        r"\bshopify\b",
    )

    app_skill_patterns = (
        r"\bmobile\s+app(?:lication)?\s+development\b",
        r"\bandroid\s+app(?:lication)?\s+development\b",
        r"\bios\s+app(?:lication)?\s+development\b",
        r"\biphone\s+app(?:lication)?\s+development\b",
        r"\bflutter\s+app(?:lication)?\s+development\b",
        r"\breact\s+native\s+app(?:lication)?\s+development\b",
        r"\bandroid\s+development\b",
        r"\bios\s+development\b",
        r"\breact\s+native\b",
    )

    software_skill_patterns = (
        r"\bsoftware\s+development\b",
        r"\bdesktop\s+application\s+development\b",
        r"\bdesktop\s+software\s+development\b",
        r"\bwindows\s+application\s+development\b",
    )

    web_description_patterns = (
        r"\b(?:develop\w*|build\w*|create\w*|design\w*|redesign\w*)\b"
        r".{0,100}\b(?:website|web\s+app(?:lication)?|web\s+portal)\b",
        r"\b(?:website|web\s+app(?:lication)?|web\s+portal)\b"
        r".{0,100}\b(?:develop\w*|build\w*|create\w*|design\w*|redesign\w*)\b",
    )

    app_description_patterns = (
        r"\b(?:develop|build|create)\b"
        r".{0,100}\b(?:mobile|android|ios|iphone)\s+app(?:lication)?\b",
        r"\b(?:mobile|android|ios|iphone)\s+app(?:lication)?\b"
        r".{0,100}\b(?:develop|build|create)\b",
        r"\b(?:develop|build|create)\b"
        r".{0,100}\bflutter\s+app(?:lication)?\b",
        r"\b(?:develop|build|create)\b"
        r".{0,100}\breact\s+native\s+app(?:lication)?\b",
    )

    software_description_patterns = (
        r"\b(?:develop|build|create)\b"
        r".{0,100}\b(?:desktop|windows)\s+(?:application|software)\b",
        r"\b(desktop|windows)\s+(?:application|software)\b"
        r".{0,100}\b(?:develop|build|create)\b",
    )

    # Collect evidence from all fields before deciding.
    has_web = (
        matches(web_title_patterns, title_text)
        or matches(web_skill_patterns, technology_text)
        or matches(web_description_patterns, description_text)
    )

    has_app = (
        matches(app_title_patterns, title_text)
        or matches(app_skill_patterns, technology_text)
        or matches(app_description_patterns, description_text)
    )

    has_software = (
        matches(software_title_patterns, title_text)
        or matches(software_skill_patterns, technology_text)
        or matches(software_description_patterns, description_text)
    )

    # Prevent sales and marketing jobs from being classified as Web
    # just because the description mentions website development services.
    sales_or_marketing_role = matches(
        (
            r"\bsales\b",
            r"\blead\s+generation\b",
            r"\bmarketing\b",
            r"\bseo\s+specialist\b",
            r"\bsalesperson\b",
        ),
        title_text,
    )

    if (
        sales_or_marketing_role
        and not matches(web_title_patterns, title_text)
        and not matches(web_skill_patterns, technology_text)
    ):
        has_web = False

    if has_web and has_app:
        return "Both"

    if has_web:
        return "Web"

    if has_app:
        return "App"

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

    # Normalize both www and non-www URLs to one hostname.
    return urlunsplit(
        ("https", "truelancer.com", path, "", "")
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
    classifier = ProjectClassifier()

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

        category, confidence_score, is_relevant = classifier.classify(
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
                category=category,
                confidence_score=confidence_score,
                is_relevant=is_relevant,
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
