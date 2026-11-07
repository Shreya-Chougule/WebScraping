import pytest
from src.classifier import ProjectClassifier

def test_project_classifier():
    classifier = ProjectClassifier()

    # Test 1: Web Development Project
    category, confidence, is_relevant = classifier.classify(
        title="Looking for a React and Next.js Frontend Developer",
        description="We need a skilled developer to build a modern responsive website.",
        technologies=["React", "Next.js", "Tailwind CSS"]
    )
    assert category == "Web"
    assert is_relevant == True
    assert confidence > 0.0

    # Test 2: Mobile App Project
    category, confidence, is_relevant = classifier.classify(
        title="Flutter Mobile App for iOS and Android",
        description="Build a cross-platform mobile application using Flutter and Dart.",
        technologies=["Flutter", "Dart"]
    )
    assert category == "App"
    assert is_relevant == True

    # Test 3: Irrelevant Project
    category, confidence, is_relevant = classifier.classify(
        title="Need Content Writer for Blog",
        description="Looking for someone to write articles about cooking recipes.",
        technologies=["Writing", "SEO"]
    )
    assert category == "Other / Irrelevant"
    assert is_relevant == False