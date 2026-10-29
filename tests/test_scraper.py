
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scraper import parse_project_cards


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
    assert projects[1].project_type == "Not specified"
    assert projects[2].project_type == "Mobile App"
    assert projects[3].project_type == "Both"


def test_does_not_invent_missing_project_url():
    projects = extract_sample_projects()

    assert projects[4].original_url == "Not specified"
