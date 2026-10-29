
import json

import pytest

from src.truelancer_parser import parse_truelancer_html


def make_html(projects):
    payload = {
        "props": {
            "pageProps": {
                "data": {
                    "projects": {"data": projects}
                }
            }
        }
    }
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script></html>"
    )


def test_extracts_truelancer_project_fields():
    html = make_html([
        {
            "title": "Build a Web Application",
            "description": "Create a dashboard &amp; API",
            "budget": 102,
            "currency": "USD",
            "created_at": "2026-10-26T17:01:01.000000Z",
            "skills": [{"tagName": "Python"}, {"tagName": "FastAPI"}],
            "link": (
                "https://www.truelancer.com/freelance-project/"
                "build-a-web-application-123"
            ),
        }
    ])

    projects = parse_truelancer_html(html)

    assert len(projects) == 1
    project = projects[0]
    assert project.title == "Build a Web Application"
    assert "Create a dashboard" in project.description
    assert project.budget == "USD 102"
    assert project.posted_date == "2026-10-26"
    assert project.technologies == ["Python", "FastAPI"]
    assert project.source_name == "Truelancer"
    assert project.original_url.endswith("build-a-web-application-123")


def test_skips_records_without_titles():
    html = make_html([{"title": "", "budget": 10}])
    assert parse_truelancer_html(html) == []


def test_raises_error_when_embedded_data_is_missing():
    with pytest.raises(ValueError, match="embedded project data"):
        parse_truelancer_html("<html><body>No project data</body></html>")
