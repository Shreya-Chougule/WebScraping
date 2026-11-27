
import json

import pytest

from src.scraper import (
    extract_next_page_url,
    validate_pagination_url,
    _parse_truelancer_response,
    scrape_truelancer_pages,
)


API_PAGE_URL = "https://api.truelancer.com/api/v1/projects?page=1"
API_NEXT_PAGE_URL = "https://api.truelancer.com/api/v1/projects?page=2"


def make_api_response(
    projects=None,
    next_page_url=None,
):
    """Build a sample Truelancer API JSON response."""
    return json.dumps(
        {
            "status": 1,
            "projects": {
                "current_page": 1,
                "next_page_url": next_page_url,
                "data": projects or [],
            },
        }
    )


def test_extracts_next_page_url_from_json():
    response = make_api_response(
        next_page_url=API_NEXT_PAGE_URL
    )

    assert extract_next_page_url(response) == API_NEXT_PAGE_URL


def test_returns_none_when_json_has_no_next_page():
    response = make_api_response(
        next_page_url=None
    )

    assert extract_next_page_url(response) is None


def test_accepts_api_host_as_next_page_url():
    assert validate_pagination_url(
        API_NEXT_PAGE_URL,
        API_PAGE_URL,
    )


def test_rejects_unapproved_subdomain():
    malicious_url = (
        "https://api.truelancer.com.evil.com/api/v1/projects?page=2"
    )

    assert not validate_pagination_url(
        malicious_url,
        API_PAGE_URL,
    )


def test_accepts_api_host_as_start_url():
    assert validate_pagination_url(
        API_PAGE_URL,
        API_PAGE_URL,
    )


def test_rejects_unapproved_start_url():
    invalid_start_url = (
        "https://example.com/api/v1/projects?page=1"
    )

    assert not validate_pagination_url(
        invalid_start_url,
        invalid_start_url,
    )


def test_parses_json_response():
    response = make_api_response(
        projects=[
            {
                "id": 12345,
                "title": "Python Developer Needed",
                "description": "Build a Python application",
                "url": "https://www.truelancer.com/freelance-project/python-developer-needed",
            }
        ],
        next_page_url=API_NEXT_PAGE_URL,
    )

    projects = _parse_truelancer_response(response)

    assert len(projects) == 1
    assert projects[0].title == "Python Developer Needed"


def test_parses_json_response_without_next_page():
    response = make_api_response(
        projects=[
            {
                "id": 12346,
                "title": "React Developer",
                "description": "Build a React website",
                "url": "https://www.truelancer.com/freelance-project/react-developer",
            }
        ]
    )

    projects = _parse_truelancer_response(response)

    assert len(projects) == 1
    assert projects[0].title == "React Developer"
    assert extract_next_page_url(response) is None


def test_html_page_followed_by_json_api_page():
    html_response = """
    <html>
      <body>
        <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "pageProps": {
                "data": {
                  "projects": {
                    "next_page_url":
                      "https://api.truelancer.com/api/v1/projects?page=2"
                  }
                }
              }
            }
          }
        </script>
      </body>
    </html>
    """

    assert extract_next_page_url(html_response) == API_NEXT_PAGE_URL

    json_response = make_api_response(
        projects=[
            {
                "id": 12347,
                "title": "Backend Developer",
                "description": "Build a backend API",
                "url": "https://www.truelancer.com/freelance-project/backend-developer",
            }
        ]
    )

    projects = _parse_truelancer_response(json_response)

    assert len(projects) == 1
    assert projects[0].title == "Backend Developer"


def test_multiple_json_api_pages_have_valid_next_urls():
    page_one = make_api_response(
        next_page_url=API_NEXT_PAGE_URL
    )

    page_two = make_api_response(
        next_page_url=None
    )

    assert extract_next_page_url(page_one) == API_NEXT_PAGE_URL
    assert extract_next_page_url(page_two) is None

    assert validate_pagination_url(
        extract_next_page_url(page_one),
        API_PAGE_URL,
    )


def test_rejects_external_pagination_url():
    external_url = "https://example.com/projects?page=2"

    assert not validate_pagination_url(
        external_url,
        API_PAGE_URL,
    )


def test_rejects_non_http_pagination_url():
    invalid_url = "javascript:alert(1)"

    assert not validate_pagination_url(
        invalid_url,
        API_PAGE_URL,
    )
