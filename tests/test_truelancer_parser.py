
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
            "currency": "usd",
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
    assert project.description == "Create a dashboard & API"
    assert project.budget == "102"
    assert project.currency == "USD"
    assert project.posted_date == "2026-10-26"
    assert project.technologies == ["Python", "FastAPI"]
    assert project.category == "Web"
    assert project.confidence_score is not None
    assert project.confidence_score > 0
    assert project.is_relevant is True
    assert project.source_name == "Truelancer"
    assert project.original_url.endswith("build-a-web-application-123")


def test_missing_optional_fields_are_none():
    html = make_html([
        {
            "title": "Build a custom solution",
            "link": (
                "https://www.truelancer.com/freelance-project/"
                "custom-solution-456"
            ),
        }
    ])

    projects = parse_truelancer_html(html)

    assert len(projects) == 1
    project = projects[0]

    assert project.description is None
    assert project.budget is None
    assert project.currency is None
    assert project.posted_date is None
    assert project.deadline is None
    assert project.project_type is None
    assert project.technologies == []


def test_skips_records_without_titles():
    html = make_html([{"title": "", "budget": 10}])
    assert parse_truelancer_html(html) == []


def test_raises_error_when_embedded_data_is_missing():
    with pytest.raises(ValueError, match="embedded project data"):
        parse_truelancer_html("<html><body>No project data</body></html>")

def test_irrelevant_truelancer_project_is_classified():
    html = make_html([
        {
            "title": "Content Writer Needed",
            "description": "Write blog articles about cooking.",
            "link": (
                "https://www.truelancer.com/freelance-project/"
                "content-writer-789"
            ),
        }
    ])

    projects = parse_truelancer_html(html)

    assert len(projects) == 1
    assert projects[0].category == "Other / Irrelevant"
    assert projects[0].confidence_score == 0.0
    assert projects[0].is_relevant is False
