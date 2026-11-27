
import re
from typing import List, Optional, Tuple


class ProjectClassifier:
    def __init__(self):
        self.keywords = {
            "web": [
                "react", "next.js", "vue", "angular", "html", "css",
                "javascript", "typescript", "wordpress", "shopify",
                "web app", "web application", "django", "fastapi",
                "flask", "node.js", "website", "landing page",
                "e-commerce", "web development", "frontend"
            ],
            "app": [
                "flutter", "react native", "swift", "kotlin",
                "mobile app", "android app", "ios app",
                "flutter app", "cross-platform", "mobile application",
                "android development", "ios development",
                "android developer", "ios developer",
                "android app development", "ios app development",
                "mobile app development", "mobile application development",
                "mobile development", "mobile developer"
            ],
            "software": [
                "python", "java", "c++", "c#", "backend", "api",
                "database", "automation", "script",
                "machine learning", "ai", "data science",
                "software development", "desktop application"
            ]
        }

    def classify(
        self,
        title: str,
        description: Optional[str] = "",
        technologies: List[str] = None
    ) -> Tuple[str, float, bool]:
        """
        Classifies a project into Web, App, Software, Both,
        or Other / Irrelevant.

        Returns:
            (category, confidence_score, is_relevant)
        """
        text = (
            f"{title} {description or ''} "
            f"{' '.join(technologies or [])}"
        ).lower()

        scores = {
            "web": 0,
            "app": 0,
            "software": 0
        }

        # Match keywords using word boundaries.
        for category, words in self.keywords.items():
            for word in words:
                pattern = r"(?<!\w)" + re.escape(word) + r"(?!\w)"

                if re.search(pattern, text):
                    scores[category] += 1

        total_matches = sum(scores.values())

        if total_matches == 0:
            return "Other / Irrelevant", 0.0, False

        matched_categories = [
            category
            for category, score in scores.items()
            if score > 0
        ]

        if (
            len(matched_categories) > 1
            and "web" in matched_categories
            and "app" in matched_categories
        ):
            category = "Both"
        elif len(matched_categories) == 1:
            category = matched_categories[0].capitalize()
        else:
            category = max(scores, key=scores.get).capitalize()

        confidence = min(round(total_matches * 0.25, 2), 1.0)
        is_relevant = confidence > 0.15

        return category, confidence, is_relevant
