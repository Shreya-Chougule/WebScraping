
import hashlib
from typing import List, Optional, Tuple

from rapidfuzz import fuzz


class ProjectDeduplicator:
    def __init__(self, similarity_threshold: float = 85.0):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _clean(value: Optional[str]) -> str:
        """Safely normalize optional text values."""
        if not isinstance(value, str):
            return ""
        return " ".join(value.strip().lower().split())

    def generate_content_hash(
        self,
        title: Optional[str],
        description: Optional[str] = "",
    ) -> str:
        """Generate an MD5 hash from normalized project content."""
        normalized_title = self._clean(title)
        normalized_description = self._clean(description)

        normalized_text = (
            f"{normalized_title} {normalized_description}"
        ).strip()

        return hashlib.md5(
            normalized_text.encode("utf-8")
        ).hexdigest()

    def is_duplicate(
        self,
        new_project: dict,
        existing_projects: List[dict],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check duplicates using:
        1. Exact URL
        2. Normalized content hash
        3. Fuzzy title similarity
        """
        new_url = self._clean(new_project.get("original_url"))
        new_title = self._clean(new_project.get("title"))
        new_description = self._clean(new_project.get("description"))

        # Avoid false matches for records with no identifying content.
        if not new_title and not new_description and not new_url:
            return False, None

        new_hash = (
            self.generate_content_hash(new_title, new_description)
            if new_title or new_description
            else None
        )

        for existing in existing_projects:
            existing_url = self._clean(
                existing.get("original_url")
            )

            # 1. Exact URL match
            if new_url and existing_url and new_url == existing_url:
                return True, "Duplicate URL match"

            existing_title = self._clean(existing.get("title"))
            existing_description = self._clean(
                existing.get("description")
            )

            # 2. Content hash match
            existing_hash = existing.get("content_hash")

            if not existing_hash and (
                existing_title or existing_description
            ):
                existing_hash = self.generate_content_hash(
                    existing_title,
                    existing_description,
                )

            if (
                new_hash
                and existing_hash
                and new_hash == existing_hash
            ):
                return True, "Duplicate Content Hash match"

            # 3. Fuzzy title similarity
            if new_title and existing_title:
                similarity = fuzz.ratio(
                    new_title,
                    existing_title,
                )

                if similarity >= self.similarity_threshold:
                    return (
                        True,
                        f"Fuzzy similarity match ({similarity:.1f}%)",
                    )

        return False, None
