import re
from typing import List, Optional, Tuple

class ProjectClassifier:
    def __init__(self):
        # Category-wise keywords definition for ScrapeScout
        self.keywords = {
            "web": [
                "react", "next.js", "vue", "angular", "html", "css", "javascript",
                "typescript", "wordpress", "shopify", "web app", "web application", "django", "fastapi", "flask",
                "node.js", "website", "landing page", "e-commerce", "web development", "frontend"
            ],
            "app": [
                "flutter", "react native", "android", "ios", "swift", "kotlin",
                "mobile app", "android app", "ios app", "flutter app", "cross-platform", "mobile application"
            ],
            "software": [
                "python", "java", "c++", "c#", "backend", "api", "database",
                "automation", "script", "machine learning", "ai", "data science",
                "software development", "desktop application"
            ]
        }

    def classify(self, title: str, description: Optional[str] = "", technologies: List[str] = None) -> Tuple[str, float, bool]:
        """
        Classifies a project into Web, App, Software, Both, or Other / Irrelevant.
        Returns: (category, confidence_score, is_relevant)
        """
        # Combine all text for searching keywords
        text = f"{title} {description or ''} {' '.join(technologies or [])}".lower()

        scores = {"web": 0, "app": 0, "software": 0}

        # Count keyword matches for each category using word boundaries
        for category, words in self.keywords.items():
            for word in words:
               if re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', text):
                    scores[category] += 1

        total_matches = sum(scores.values())

        # If no keywords matched at all
        if total_matches == 0:
            return "Other / Irrelevant", 0.0, False

        # Determine dominant categories
        matched_categories = [cat for cat, score in scores.items() if score > 0]

        if len(matched_categories) > 1 and "web" in matched_categories and "app" in matched_categories:
            category = "Both"
        elif len(matched_categories) == 1:
            category = matched_categories[0].capitalize()
        else:
            # Pick the highest scoring category
            category = max(scores, key=scores.get).capitalize()

        # Calculate a simple confidence score (capped at 1.0)
        confidence = min(round(total_matches * 0.25, 2), 1.0)
        is_relevant = confidence > 0.15

        return category, confidence, is_relevant
