
import json

import pytest

from src.truelancer_parser import (
    infer_truelancer_project_type,
    parse_truelancer_html,
)


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
    assert project.project_type == "Web"
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
    assert projects[0].project_type is None


@pytest.mark.parametrize(
    "title,description,technologies,expected",
    [
        (
            "Develop 24x7 Gameplay Bots Using Strategy",
            "",
            ["Android App Development", "Automation"],
            "App",
        ),
        (
            "Mobile App Developer Needed",
            "",
            ["Flutter", "Dart"],
            "App",
        ),
        (
            "Frontend Developer Needed",
            "",
            ["React", "HTML", "CSS"],
            "Web",
        ),
        (
            "Website Redesign Project",
            "",
            ["WordPress"],
            "Web",
        ),
        (
            "Build a Mobile Application",
            "We also need a website developed for the same service.",
            [],
            "Both",
        ),
        (
            "Develop a Desktop Application",
            "",
            ["Python"],
            "Software",
        ),
        (
            "Python Developer for Automation",
            "Create an automated trading script.",
            ["Python", "Automation"],
            None,
        ),
        (
            "Web Scraping Specialist",
            "Extract public listing information from websites.",
            ["Web Scraping", "Python"],
            None,
        ),
        (
            "JavaScript Developer",
            "Build a custom automation script.",
            ["JavaScript", "Node.js"],
            None,
        ),
    ],
)
def test_infers_project_type_from_explicit_evidence(
    title,
    description,
    technologies,
    expected,
):
    result = infer_truelancer_project_type(
        title=title,
        description=description,
        technologies=technologies,
    )

    assert result == expected


def test_parser_recognizes_android_app_development_skill():
    html = make_html([
        {
            "title": "Develop 24x7 Gameplay Bots Using Strategy",
            "description": "Create gameplay bots using strategy algorithms.",
            "skills": [
                {"tagName": "Android App Development"},
                {"tagName": "Automation"},
            ],
            "link": (
                "https://www.truelancer.com/freelance-project/"
                "gameplay-bots-101"
            ),
        }
    ])

    projects = parse_truelancer_html(html)

    assert len(projects) == 1
    assert projects[0].project_type == "App"
    assert "Android App Development" in projects[0].technologies


def test_duplicate_project_urls_are_removed():
    project = {
        "title": "Build a Website",
        "description": "Create a business website.",
        "link": (
            "https://www.truelancer.com/freelance-project/"
            "build-website-123"
        ),
    }

    duplicate = {
        **project,
        "link": (
            "https://truelancer.com/freelance-project/"
            "build-website-123/"
        ),
    }

    projects = parse_truelancer_html(make_html([project, duplicate]))

    assert len(projects) == 1


def test_sales_job_is_not_classified_as_web_from_service_mention():
    result = infer_truelancer_project_type(
        title="Sales and Lead Generation Specialist for Tech Services",
        description=(
            "Generate leads and drive sales for our website "
            "development, tool development, and SEO services."
        ),
        technologies=[
            "Sales",
            "Lead Generation",
            "Salesmen",
            "Business Strategy",
        ],
    )

    assert result is None
