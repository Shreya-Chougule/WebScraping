import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scraper import parse_project_cards

sample_html = """
<div class="project">
    <h2><a href="/project/123">Build a React Website</a></h2>
    <p class="description">Create a responsive website for a small business.</p>
    <span class="budget">$500 - $800</span>
    <span class="technology">React</span>
    <span class="technology">CSS</span>
</div>
<div class="project">
    <h2><a href="/project/456">Python Automation Script</a></h2>
    <p class="description">Automate a repetitive reporting task.</p>
</div>
"""

projects = parse_project_cards(
    html=sample_html,
    source_name="Local HTML Test",
    base_url="https://example.com",
    card_selector=".project",
    title_selector="h2",
    description_selector=".description",
    budget_selector=".budget",
    technologies_selector=".technology",
)

for project in projects:
    print(project.to_dict())

assert len(projects) == 2
assert projects[0].title == "Build a React Website"
assert projects[0].budget == "$500 - $800"
assert projects[0].technologies == ["React", "CSS"]
assert projects[1].budget is None

print("\nAll scraper extraction tests passed!")