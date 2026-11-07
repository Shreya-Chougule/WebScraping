import pytest
from src.deduplicator import ProjectDeduplicator

def test_deduplicator_matching():
    deduplicator = ProjectDeduplicator(similarity_threshold=85.0)

    # Existing records in database / list
    existing_projects = [
        {
            "title": "Build a React Web Application",
            "description": "We need a frontend developer using React and Tailwind CSS.",
            "original_url": "https://example.com/project/1"
        }
    ]

    # Test 1: Exact URL Match
    new_project_url = {
        "title": "Completely Different Title",
        "description": "Some random description.",
        "original_url": "https://example.com/project/1"
    }
    is_dup, reason = deduplicator.is_duplicate(new_project_url, existing_projects)
    assert is_dup == True
    assert "URL" in reason

    # Test 2: Content Hash Match (Same title & description, different URL)
    new_project_hash = {
        "title": "Build a React Web Application",
        "description": "We need a frontend developer using React and Tailwind CSS.",
        "original_url": "https://example.com/project/2"
    }
    is_dup, reason = deduplicator.is_duplicate(new_project_hash, existing_projects)
    assert is_dup == True
    assert "Hash" in reason

    # Test 3: Fuzzy Similarity Match (Very close variation of title)
    new_project_fuzzy = {
        "title": "Build a React Web Application!",  # Added exclamation/minor change
        "description": "Different description text here.",
        "original_url": "https://example.com/project/3"
    }
    is_dup, reason = deduplicator.is_duplicate(new_project_fuzzy, existing_projects)
    assert is_dup == True
    assert "Fuzzy" in reason

    # Test 4: Completely Unique Project (No Duplicate)
    new_project_unique = {
        "title": "Develop Mobile App with Flutter",
        "description": "Need an Android and iOS developer.",
        "original_url": "https://example.com/project/4"
    }
    is_dup, reason = deduplicator.is_duplicate(new_project_unique, existing_projects)
    assert is_dup == False
    assert reason is None


def test_handles_none_and_missing_fields():
    deduplicator = ProjectDeduplicator()

    result, reason = deduplicator.is_duplicate(
        {
            "title": None,
            "description": None,
            "original_url": None,
        },
        [
            {
                "title": None,
                "description": None,
                "original_url": None,
            }
        ],
    )

    assert result is False
    assert reason is None


def test_empty_projects_are_not_false_duplicates():
    deduplicator = ProjectDeduplicator()

    result, reason = deduplicator.is_duplicate(
        {
            "title": "",
            "description": "",
            "original_url": "",
        },
        [
            {
                "title": "",
                "description": "",
                "original_url": "",
            }
        ],
    )

    assert result is False
    assert reason is None


def test_normalized_content_detects_duplicate():
    deduplicator = ProjectDeduplicator()

    existing = [
        {
            "title": "  Build a React Website ",
            "description": " Create a responsive website ",
        }
    ]

    new_project = {
        "title": "build a react website",
        "description": "create a responsive website",
    }

    result, reason = deduplicator.is_duplicate(
        new_project,
        existing,
    )

    assert result is True
    assert "Hash" in reason


def test_missing_title_does_not_trigger_fuzzy_match():
    deduplicator = ProjectDeduplicator()

    result, reason = deduplicator.is_duplicate(
        {
            "title": None,
            "description": "A completely different project",
        },
        [
            {
                "title": None,
                "description": "Another different project",
            }
        ],
    )

    assert result is False
    assert reason is None
