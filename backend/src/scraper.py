
from pathlib import Path
from functools import partial
from typing import Optional
from urllib.parse import urljoin, urlparse
import json
import os
import time

import requests
from bs4 import BeautifulSoup

from src.classifier import ProjectClassifier
from src.deduplicator import ProjectDeduplicator
from src.extraction_schema import (
    ExtractedProject,
    save_projects_csv,
    save_projects_json,
)
from src.supabase_mapper import map_project_to_supabase
from src.truelancer_parser import (
    parse_truelancer_html,
    parse_truelancer_json,
)
from src.scraperapi_provider import fetch_page_via_scraperapi


# ============================================================
# BACKEND API CONFIGURATION
# ============================================================

API_BASE_URL = os.getenv(
    "SCRAPESCOUT_API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

API_ENDPOINT = f"{API_BASE_URL}/projects"
SOURCE_ENDPOINT = f"{API_BASE_URL}/sources"
SCRAPING_RUNS_ENDPOINT = f"{API_BASE_URL}/scraping-runs"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"

API_EMAIL_ENV = "SCRAPESCOUT_API_EMAIL"
API_PASSWORD_ENV = "SCRAPESCOUT_API_PASSWORD"

API_TOKEN_CACHE_SECONDS = 23 * 60 * 60

_cached_api_token: Optional[str] = None
_api_token_expires_at = 0.0


class APIAuthenticationError(requests.RequestException):
    """Raised when the scraper cannot authenticate with the backend API."""


def _production_auth_required() -> bool:
    """Determine whether missing scraper credentials must stop API calls."""
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    auth_required = os.getenv(
        "AUTH_REQUIRED",
        "false",
    ).strip().lower()

    return environment == "production" or auth_required == "true"


def get_api_headers() -> dict[str, str]:
    """Return backend API authentication headers."""
    global _cached_api_token, _api_token_expires_at

    email = os.getenv(API_EMAIL_ENV)
    password = os.getenv(API_PASSWORD_ENV)

    if not email or not password:
        if _production_auth_required():
            raise APIAuthenticationError(
                "Backend API authentication is required. "
                f"Configure {API_EMAIL_ENV} and {API_PASSWORD_ENV}."
            )

        return {}

    if _cached_api_token and time.monotonic() < _api_token_expires_at:
        return {
            "Authorization": f"Bearer {_cached_api_token}",
        }

    try:
        response = requests.post(
            LOGIN_ENDPOINT,
            json={
                "email": email.strip().lower(),
                "password": password,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        login_data = response.json()
        access_token = login_data.get("access_token")

        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError(
                "Login response did not contain a valid access token."
            )

        _cached_api_token = access_token
        _api_token_expires_at = (
            time.monotonic() + API_TOKEN_CACHE_SECONDS
        )

        return {
            "Authorization": f"Bearer {_cached_api_token}",
        }

    except (requests.RequestException, ValueError) as exc:
        _cached_api_token = None
        _api_token_expires_at = 0.0

        raise APIAuthenticationError(
            "Could not authenticate the scraper with the backend API. "
            "Check the configured API URL and automation account."
        ) from exc


def _api_request_kwargs() -> dict:
    """Return optional request arguments."""
    headers = get_api_headers()

    if not headers:
        return {}

    return {"headers": headers}


def reset_api_token_cache() -> None:
    """Clear the cached token. Primarily useful for tests and re-login."""
    global _cached_api_token, _api_token_expires_at

    _cached_api_token = None
    _api_token_expires_at = 0.0


# ============================================================
# GENERAL CONFIGURATION
# ============================================================

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

NOT_SPECIFIED = "Not specified"
REQUEST_TIMEOUT = 15
USER_AGENT = "ScrapeScout/1.0 (Educational Project)"

ALLOWED_TRUELANCER_HOSTS = {
    "truelancer.com",
    "www.truelancer.com",
    "api.truelancer.com",
}


ALLOWED_TRUELANCER_START_HOSTS = {
    "truelancer.com",
    "www.truelancer.com",
    "api.truelancer.com",
}


class ScrapingAccessError(Exception):
    """Raised when a website blocks or restricts a scraping request."""


# ============================================================
# GENERAL SCRAPING FUNCTIONS
# ============================================================

def fetch_page(
    url: str,
    timeout: int = REQUEST_TIMEOUT,
) -> str:
    """Fetch a public webpage safely without automatically following redirects."""
    try:
        parsed = urlparse(url)

        if parsed.scheme == "https":
            valid_port = parsed.port in (None, 443)
        elif parsed.scheme == "http":
            valid_port = parsed.port in (None, 80)
        else:
            valid_port = False

    except ValueError:
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or not valid_port
        or any(char.isspace() for char in url)
    ):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=timeout,
        allow_redirects=False,
    )

    if response.status_code in (403, 429):
        raise ScrapingAccessError(
            f"Website restricted the request: HTTP {response.status_code}."
        )

    if 300 <= response.status_code < 400:
        raise ScrapingAccessError(
            "The website returned a redirect. "
            "It was not followed automatically."
        )

    response.raise_for_status()

    page_text = response.text.lower()

    restricted_markers = (
        "vercel security checkpoint",
        "verify you are human",
        "security checkpoint",
    )

    if any(marker in page_text for marker in restricted_markers):
        raise ScrapingAccessError(
            "A security checkpoint was detected. "
            "The page was not scraped."
        )

    return response.text


classifier = ProjectClassifier()


def clean_text(value: Optional[str]) -> Optional[str]:
    """Remove HTML markup, normalize whitespace and return None if empty."""
    if not value:
        return None

    cleaned = BeautifulSoup(value, "html.parser").get_text(" ")
    cleaned = " ".join(cleaned.split())

    return cleaned or None


def infer_project_type(
    title: str,
    description: Optional[str] = None,
    technologies: Optional[list[str]] = None,
) -> Optional[str]:
    """Infer the likely project type from available information."""
    text = " ".join(
        part
        for part in [
            title,
            description or "",
            " ".join(technologies or []),
        ]
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

    software_terms = (
        "software",
        "desktop application",
        "desktop app",
        "windows application",
        "windows software",
    )

    has_web = any(term in text for term in web_terms)
    has_mobile = any(term in text for term in mobile_terms)
    has_software = any(term in text for term in software_terms)

    if has_web and has_mobile:
        return "Both"

    if has_software:
        return "Software"

    if has_web:
        return "Web"

    if has_mobile:
        return "Mobile App"

    return None


def resolve_project_url(
    base_url: str,
    href: Optional[str],
) -> Optional[str]:
    """Resolve a relative project link and validate its URL."""
    if not isinstance(href, str) or not href.strip():
        return None

    resolved_url = urljoin(base_url, href.strip())

    try:
        parsed = urlparse(resolved_url)

        if parsed.scheme == "https":
            valid_port = parsed.port in (None, 443)
        elif parsed.scheme == "http":
            valid_port = parsed.port in (None, 80)
        else:
            valid_port = False

    except ValueError:
        return None

    if (
        not valid_port
        or parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(char.isspace() for char in resolved_url)
    ):
        return None

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

        link_element = (
            title_element
            if title_element.name == "a"
            else title_element.find("a")
        )

        href = link_element.get("href") if link_element else None
        original_url = resolve_project_url(base_url, href)

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

        category, confidence_score, is_relevant = classifier.classify(
            title=title,
            description=description,
            technologies=technologies,
        )

        project = ExtractedProject(
            title=title,
            description=description or NOT_SPECIFIED,
            budget=budget or NOT_SPECIFIED,
            currency=None,
            posted_date=posted_date or NOT_SPECIFIED,
            deadline=deadline or NOT_SPECIFIED,
            technologies=technologies,
            project_type=project_type,
            source_name=source_name or NOT_SPECIFIED,
            original_url=original_url,
            category=category,
            confidence_score=confidence_score,
            is_relevant=is_relevant,
        )

        projects.append(project)

    return projects


# ============================================================
# EXPORT AND API SUBMISSION
# ============================================================

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
    source_endpoint: str = SOURCE_ENDPOINT,
) -> dict[str, int]:
    """Submit eligible projects to the FastAPI backend."""
    results = {
        "total": len(projects),
        "inserted": 0,
        "duplicate_skipped": 0,
        "irrelevant_skipped": 0,
        "missing_url_skipped": 0,
        "source_not_found_skipped": 0,
        "invalid_skipped": 0,
        "failed": 0,
    }

    if not projects:
        print("[INFO] No projects to submit.")
        return results

    try:
        request_kwargs = _api_request_kwargs()

        source_response = requests.get(
            source_endpoint,
            timeout=REQUEST_TIMEOUT,
            **request_kwargs,
        )
        source_response.raise_for_status()
        sources = source_response.json()

        if not isinstance(sources, list):
            raise ValueError("Sources API did not return a list.")

    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] Could not retrieve sources: {exc}")
        results["failed"] = len(projects)
        return results

    source_lookup = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        name = source.get("name")
        src_id = source.get("id")
        if not name or not src_id:
            continue
        key = name.strip().casefold()
        if source.get("is_active") is True or key not in source_lookup:
            source_lookup[key] = src_id

    try:
        existing_response = requests.get(
            api_endpoint,
            timeout=REQUEST_TIMEOUT,
            **request_kwargs,
        )
        existing_response.raise_for_status()
        existing_projects = existing_response.json()

        if not isinstance(existing_projects, list):
            raise ValueError("Projects API did not return a list.")

    except (requests.RequestException, ValueError) as exc:
        print(f"[ERROR] Could not retrieve existing projects: {exc}")
        print("[STOPPED] No projects were submitted.")
        results["failed"] = len(projects)
        return results

    deduplicator = ProjectDeduplicator()

    for project in projects:
        if not project.is_relevant:
            print(f"[SKIPPED] Irrelevant project: {project.title}")
            results["irrelevant_skipped"] += 1
            continue

        if (
            not isinstance(project.original_url, str)
            or not project.original_url.strip()
            or project.original_url.strip() == NOT_SPECIFIED
        ):
            print(f"[SKIPPED] Missing project URL: {project.title}")
            results["missing_url_skipped"] += 1
            continue

        source_id = source_lookup.get(
            project.source_name.strip().casefold()
            if project.source_name
            else ""
        )

        if not source_id:
            print(f"[SKIPPED] Source not found: {project.source_name}")
            results["source_not_found_skipped"] += 1
            continue

        try:
            payload = map_project_to_supabase(project, source_id)

            is_duplicate, duplicate_reason = deduplicator.is_duplicate(
                payload,
                existing_projects,
            )

            if is_duplicate:
                print(
                    f"[SKIPPED] Duplicate project: {project.title} "
                    f"({duplicate_reason})"
                )
                results["duplicate_skipped"] += 1
                continue

            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                **request_kwargs,
            )

            if response.status_code in (200, 201):
                print(f"[SUCCESS] Inserted: {project.title}")
                existing_projects.append(payload)
                results["inserted"] += 1

            elif response.status_code == 409:
                print(f"[SKIPPED] Duplicate project: {project.title}")
                results["duplicate_skipped"] += 1

            elif response.status_code == 400:
                print(f"[SKIPPED] Request rejected: {project.title}")
                print(response.text)
                results["invalid_skipped"] += 1

            else:
                print(
                    f"[ERROR] HTTP {response.status_code}: "
                    f"{project.title} - {response.text}"
                )
                results["failed"] += 1

        except ValueError as exc:
            print(
                f"[SKIPPED] Invalid project data: "
                f"{project.title} - {exc}"
            )
            results["invalid_skipped"] += 1

        except requests.RequestException as exc:
            print(f"[ERROR] API request failed: {exc}")
            results["failed"] += 1

    print(f"[SUMMARY] Submission results: {results}")
    return results


# ============================================================
# PHASE 4: PAGINATION AND RESPONSE PARSING
# ============================================================

def extract_next_page_url(response_text: str) -> Optional[str]:
    """Extract the next-page URL from either Truelancer JSON or HTML."""
    try:
        data = json.loads(response_text)

        if isinstance(data, dict):
            pagination = data.get("projects")

            if isinstance(pagination, dict):
                next_url = pagination.get("next_page_url")

                if isinstance(next_url, str) and next_url.strip():
                    return next_url.strip()

                return None

    except (json.JSONDecodeError, TypeError):
        pass

    soup = BeautifulSoup(response_text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if script is None or not script.string:
        return None

    try:
        data = json.loads(script.string)
        pagination = data["props"]["pageProps"]["data"]["projects"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    if not isinstance(pagination, dict):
        return None

    next_url = pagination.get("next_page_url")

    if not isinstance(next_url, str) or not next_url.strip():
        return None

    return next_url.strip()


def validate_pagination_url(
    next_url: str,
    start_url: str,
) -> bool:
    """
    Validate Truelancer pagination URLs.

    The starting URL must use the main Truelancer website.
    Subsequent URLs may use an explicitly approved Truelancer host,
    including api.truelancer.com.
    """
    try:
        next_parts = urlparse(next_url)
        start_parts = urlparse(start_url)

        next_port = next_parts.port
        start_port = start_parts.port

    except (TypeError, ValueError):
        return False

    if next_parts.scheme != "https" or start_parts.scheme != "https":
        return False

    if not next_parts.hostname or not start_parts.hostname:
        return False

    next_hostname = next_parts.hostname.lower()
    start_hostname = start_parts.hostname.lower()

    if start_hostname not in ALLOWED_TRUELANCER_START_HOSTS:
        return False

    if next_hostname not in ALLOWED_TRUELANCER_HOSTS:
        return False

    if next_parts.username is not None or next_parts.password is not None:
        return False

    if start_parts.username is not None or start_parts.password is not None:
        return False

    if any(char.isspace() for char in next_url):
        return False

    if any(char.isspace() for char in start_url):
        return False

    if next_port not in (None, 443) or start_port not in (None, 443):
        return False

    return True


def _parse_truelancer_response(
    response_text: str,
) -> list[ExtractedProject]:
    """Choose the correct parser for a Truelancer HTML or JSON response."""
    try:
        data = json.loads(response_text)

    except json.JSONDecodeError:
        return parse_truelancer_html(response_text)

    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise ValueError(
            "Unexpected Truelancer JSON response structure."
        )

    return parse_truelancer_json(data)


def resolve_page_fetcher(
    provider: Optional[str] = None,
    fetcher=None,
    scraperapi_key: Optional[str] = None,
    render_js: bool = False,
    country_code: Optional[str] = None,
):
    """Resolve the page-fetching implementation."""
    if fetcher is not None:
        return fetcher

    selected_provider = (
        provider
        if provider is not None
        else os.getenv("SCRAPING_PROVIDER", "direct")
    )

    selected_provider = selected_provider.strip().lower()

    if selected_provider in ("direct", "requests"):
        return fetch_page

    if selected_provider in ("scraperapi", "scraper_api", "scraper-api"):
        return partial(
            fetch_page_via_scraperapi,
            api_key=scraperapi_key,
            render_js=render_js,
            country_code=country_code,
        )

    raise ValueError(
        f"Unknown scraping provider '{selected_provider}'"
    )


def scrape_truelancer_pages(
    start_url: str,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
    fetcher=None,
    sleep_fn=None,
    provider: Optional[str] = None,
    scraperapi_key: Optional[str] = None,
    render_js: bool = False,
    country_code: Optional[str] = None,
) -> list[ExtractedProject]:
    """Fetch and parse multiple Truelancer HTML or JSON pages."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    if min_request_interval < 0:
        raise ValueError("min_request_interval cannot be negative.")

    if not validate_pagination_url(start_url, start_url):
        raise ValueError("A valid HTTPS Truelancer URL is required.")

    fetch_page_function = resolve_page_fetcher(
        provider=provider,
        fetcher=fetcher,
        scraperapi_key=scraperapi_key,
        render_js=render_js,
        country_code=country_code,
    )

    sleep_function = sleep_fn or time.sleep

    current_url = start_url
    projects = []
    seen_urls = set()

    for page_number in range(max_pages):
        if page_number > 0 and min_request_interval > 0:
            sleep_function(min_request_interval)

        print(
            f"[INFO] Fetching Truelancer page "
            f"{page_number + 1}: {current_url}"
        )

        response_text = fetch_page_function(current_url)

        page_projects = _parse_truelancer_response(response_text)

        for project in page_projects:
            project_url = project.original_url

            if project_url and project_url in seen_urls:
                continue

            if project_url:
                seen_urls.add(project_url)

            projects.append(project)

        if page_number + 1 >= max_pages:
            break

        next_url = extract_next_page_url(response_text)

        if not next_url:
            print("[INFO] No additional page available.")
            break

        if not validate_pagination_url(next_url, start_url):
            raise ScrapingAccessError(
                "Pagination stopped because the next-page URL "
                "is not an approved HTTPS Truelancer URL."
            )

        current_url = next_url

    print(f"[INFO] Total unique projects extracted: {len(projects)}")

    return projects


# ============================================================
# PHASE 4: SCRAPING-RUN LOGGING THROUGH FASTAPI
# ============================================================

def create_scraping_run(
    source_id: str,
    api_endpoint: str = SCRAPING_RUNS_ENDPOINT,
) -> str:
    """Create a RUNNING scraping record through the FastAPI backend."""
    response = requests.post(
        api_endpoint,
        json={
            "source_id": source_id,
            "status": "RUNNING",
        },
        timeout=REQUEST_TIMEOUT,
        **_api_request_kwargs(),
    )

    response.raise_for_status()

    run_data = response.json()
    run_id = run_data.get("id")

    if not run_id:
        raise ValueError("Scraping-run API returned no run ID.")

    return run_id


def update_scraping_run(
    run_id: str,
    status: str,
    records_found: int,
    error_log: Optional[str] = None,
    api_endpoint: str = SCRAPING_RUNS_ENDPOINT,
) -> None:
    """Update a scraping run through the FastAPI backend."""
    if status not in ("SUCCESS", "FAILED"):
        raise ValueError("Invalid scraping-run completion status.")

    if records_found < 0:
        raise ValueError("records_found cannot be negative.")

    payload = {
        "status": status,
        "records_found": records_found,
        "error_log": error_log,
    }

    response = requests.patch(
        f"{api_endpoint}/{run_id}",
        json=payload,
        timeout=REQUEST_TIMEOUT,
        **_api_request_kwargs(),
    )

    response.raise_for_status()


def run_truelancer_scraping(
    source_id: str,
    start_url: str,
    max_pages: int = 3,
    min_request_interval: float = 1.0,
    api_endpoint: str = SCRAPING_RUNS_ENDPOINT,
    fetcher=None,
    sleep_fn=None,
) -> list[ExtractedProject]:
    """Execute a scraping run and record its status through FastAPI."""
    run_id = create_scraping_run(
        source_id=source_id,
        api_endpoint=api_endpoint,
    )

    try:
        projects = scrape_truelancer_pages(
            start_url=start_url,
            max_pages=max_pages,
            min_request_interval=min_request_interval,
            fetcher=fetcher,
            sleep_fn=sleep_fn,
        )

        update_scraping_run(
            run_id=run_id,
            status="SUCCESS",
            records_found=len(projects),
            api_endpoint=api_endpoint,
        )

        return projects

    except Exception as exc:
        try:
            update_scraping_run(
                run_id=run_id,
                status="FAILED",
                records_found=0,
                error_log=str(exc)[:5000],
                api_endpoint=api_endpoint,
            )
        except Exception as logging_error:
            print(
                "[ERROR] Could not update failed scraping run: "
                f"{logging_error}"
            )

        raise


if __name__ == "__main__":
    print("ScrapeScout extraction module is ready.")
    print(
        "Configure selectors for an approved source "
        "before fetching live pages."
    )
    print("ScrapeScout extraction and classification module is ready.")
