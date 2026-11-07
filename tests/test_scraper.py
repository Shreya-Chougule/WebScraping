import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraper import (
    ScrapingAccessError,
    clean_text,
    fetch_page,
    infer_project_type,
    parse_project_cards,
    resolve_project_url,
)


SAMPLE_HTML = """
<div class="project">
    <h2><a href="/project/123">Build a React Website</a></h2>
    <p class="description">Create a responsive website for a small business.</p>
    <span class="budget">$500 - $800</span>
    <span class="technology">React</span>
    <span class="technology">CSS</span>
    <span class="technology">React</span>
    <time class="posted" datetime="2026-10-20">20 Oct 2026</time>
    <time class="deadline" datetime="2026-11-15">15 Nov 2026</time>
</div>
<div class="project">
    <h2><a href="/project/456">Python Automation Script</a></h2>
    <p class="description">Automate a repetitive reporting task.</p>
</div>
<div class="project">
    <h2><a href="/project/789">Build an Android Mobile App</a></h2>
    <p class="description">Create a native Android mobile application.</p>
    <span class="technology">Kotlin</span>
</div>
<div class="project">
    <h2><a href="/project/999">Build a Website and Mobile App</a></h2>
    <p class="description">Develop a web app and an iOS mobile app.</p>
</div>
<div class="project">
    <h2>Project Without a Link</h2>
    <p class="description">Create a web application.</p>
</div>
"""


def extract_sample_projects():
    return parse_project_cards(
        html=SAMPLE_HTML,
        source_name="Local HTML Test",
        base_url="https://example.com/listings",
        card_selector=".project",
        title_selector="h2",
        description_selector=".description",
        budget_selector=".budget",
        technologies_selector=".technology",
        posted_date_selector=".posted",
        deadline_selector=".deadline",
    )


def test_extracts_project_details():
    projects = extract_sample_projects()

    assert len(projects) == 5
    assert projects[0].title == "Build a React Website"
    assert projects[0].description == (
        "Create a responsive website for a small business."
    )
    assert projects[0].budget == "$500 - $800"
    assert projects[0].original_url == "https://example.com/project/123"


def test_extracts_dates():
    projects = extract_sample_projects()

    assert projects[0].posted_date == "2026-10-20"
    assert projects[0].deadline == "2026-11-15"


def test_removes_duplicate_technologies():
    projects = extract_sample_projects()

    assert projects[0].technologies == ["React", "CSS"]


def test_handles_missing_fields():
    projects = extract_sample_projects()

    assert projects[1].budget == "Not specified"
    assert projects[1].posted_date == "Not specified"
    assert projects[1].deadline == "Not specified"


def test_infers_project_type():
    projects = extract_sample_projects()

    assert projects[0].project_type == "Web"
    assert projects[1].project_type is None
    assert projects[2].project_type == "Mobile App"
    assert projects[3].project_type == "Both"


def test_missing_project_url_returns_none():
    projects = extract_sample_projects()

    assert projects[4].original_url is None


def test_fetch_page_successfully():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Public page</body></html>"

    with patch("src.scraper.requests.get", return_value=mock_response) as mock_get:
        result = fetch_page("https://example.com")

    assert result == "<html><body>Public page</body></html>"
    mock_response.raise_for_status.assert_called_once()

    assert mock_get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status_code", [403, 429])
def test_fetch_page_rejects_restricted_status(status_code):
    mock_response = Mock()
    mock_response.status_code = status_code

    with patch("src.scraper.requests.get", return_value=mock_response):
        with pytest.raises(ScrapingAccessError):
            fetch_page("https://example.com")


@pytest.mark.parametrize("status_code", [301, 302, 303, 307, 308])
def test_fetch_page_rejects_redirects(status_code):
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.headers = {
        "Location": "https://example.com/redirected"
    }

    with patch(
        "src.scraper.requests.get",
        return_value=mock_response,
    ) as mock_get:

        with pytest.raises(ScrapingAccessError):
            fetch_page("https://example.com")

    assert mock_get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@example.com/page",
        "https://example.com:8443/page",
        "http://example.com:8080/page",
        "https://example.com:abc/page",
    ],
)
def test_fetch_page_rejects_credentials_or_unexpected_ports(url):
    with pytest.raises(ValueError):
        fetch_page(url)


def test_fetch_page_detects_security_checkpoint():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = (
        "<html><title>Vercel Security Checkpoint</title></html>"
    )

    with patch("src.scraper.requests.get", return_value=mock_response):
        with pytest.raises(ScrapingAccessError):
            fetch_page("https://example.com")


def test_fetch_page_rejects_invalid_url():
    with pytest.raises(ValueError):
        fetch_page("not-a-valid-url")


def test_fetch_page_handles_timeout():
    with patch(
        "src.scraper.requests.get",
        side_effect=requests.Timeout,
    ):
        with pytest.raises(requests.Timeout):
            fetch_page("https://example.com")


def test_clean_text_removes_html_and_extra_spaces():
    result = clean_text(
        "<p>  Build   a <b>website</b> </p>"
    )

    assert result == "Build a website"


def test_resolves_relative_project_url():
    result = resolve_project_url(
        "https://example.com/listings",
        "/project/123",
    )

    assert result == "https://example.com/project/123"


def test_missing_project_link_returns_none():
    result = resolve_project_url(
        "https://example.com/listings",
        None,
    )

    assert result is None


def test_blank_project_link_returns_none():
    result = resolve_project_url(
        "https://example.com/listings",
        "   ",
    )

    assert result is None


def test_invalid_project_link_returns_none():
    result = resolve_project_url(
        "https://example.com/listings",
        "javascript:alert(1)",
    )

    assert result is None


def test_project_link_with_credentials_returns_none():
    result = resolve_project_url(
        "https://example.com/listings",
        "https://user:pass@example.com/project/123",
    )

    assert result is None


def test_infers_software_project_type():
    result = infer_project_type(
        "Build a Desktop Application",
        "Create software for Windows.",
    )

    assert result == "Software"


def test_unknown_project_type_returns_none():
    result = infer_project_type(
        "Python Automation Script",
        "Automate a repetitive reporting task.",
    )

    assert result is None