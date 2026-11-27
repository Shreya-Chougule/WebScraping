
import pytest

from src.classifier import ProjectClassifier


def test_project_classifier():
    classifier = ProjectClassifier()

    # Web development project
    category, confidence, is_relevant = classifier.classify(
        title="Looking for a React and Next.js Frontend Developer",
        description="We need a skilled developer to build a modern responsive website.",
        technologies=["React", "Next.js", "Tailwind CSS"],
    )

    assert category == "Web"
    assert is_relevant is True
    assert confidence > 0.0

    # Mobile app development project
    category, confidence, is_relevant = classifier.classify(
        title="Flutter Mobile App for iOS and Android",
        description="Build a cross-platform mobile application using Flutter and Dart.",
        technologies=["Flutter", "Dart"],
    )

    assert category == "App"
    assert is_relevant is True

    # Irrelevant content-writing project
    category, confidence, is_relevant = classifier.classify(
        title="Need Content Writer for Blog",
        description="Looking for someone to write articles about cooking recipes.",
        technologies=["Writing", "SEO"],
    )

    assert category == "Other / Irrelevant"
    assert is_relevant is False


@pytest.mark.parametrize("technology", ["C++", "C#"])
def test_classifier_recognizes_punctuation_based_technologies(technology):
    classifier = ProjectClassifier()

    category, confidence, is_relevant = classifier.classify(
        title=f"Need a {technology} developer",
        description="",
        technologies=[],
    )

    assert category == "Software"
    assert confidence > 0
    assert is_relevant is True


def test_android_user_recruitment_is_irrelevant():
    classifier = ProjectClassifier()

    category, confidence, is_relevant = classifier.classify(
        title="Recruiting Android Users for Online Trading Research study",
        description="Recruiting male Android users for an online research study.",
        technologies=["Data Entry"],
    )

    assert category == "Other / Irrelevant"
    assert confidence == 0.0
    assert is_relevant is False


def test_android_app_development_is_relevant():
    classifier = ProjectClassifier()

    category, confidence, is_relevant = classifier.classify(
        title="Develop an Android App for Online Payments",
        description="Build and implement a mobile application.",
        technologies=["Android App Development", "Kotlin"],
    )

    assert category == "App"
    assert confidence > 0
    assert is_relevant is True


def test_android_app_development_skill_is_relevant():
    classifier = ProjectClassifier()

    category, confidence, is_relevant = classifier.classify(
        title="Develop a Custom Gameplay Application",
        description="Create an application using Android development.",
        technologies=["Android App Development", "Automation"],
    )

    assert category == "App"
    assert confidence > 0
    assert is_relevant is True
