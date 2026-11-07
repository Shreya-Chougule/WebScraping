import hashlib
from typing import List, Optional, Tuple
from rapidfuzz import fuzz

class ProjectDeduplicator:
    def __init__(self, similarity_threshold: float = 85.0):
        self.similarity_threshold = similarity_threshold

    def generate_content_hash(self, title: str, description: Optional[str] = "") -> str:
        """Generate an MD5 hash based on normalized title and description."""
        normalized_text = f"{title.strip().lower()} {description.strip().lower() if description else ''}"
        normalized_text = " ".join(normalized_text.split())
        return hashlib.md5(normalized_text.encode("utf-8")).hexdigest()

    def is_duplicate(
        self, 
        new_project: dict, 
        existing_projects: List[dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        Checks if a project is a duplicate based on:
        1. Exact URL match
        2. Content Hash match
        3. Fuzzy Text Similarity match
        """
        new_url = new_project.get("original_url", "").strip()
        new_title = new_project.get("title", "")
        new_desc = new_project.get("description", "")
        new_hash = self.generate_content_hash(new_title, new_desc)

        for existing in existing_projects:
            # 1. Exact URL Check
            existing_url = existing.get("original_url", "").strip()
            if new_url and existing_url and new_url == existing_url:
                return True, "Duplicate URL match"

            # 2. Content Hash Check
            existing_hash = existing.get("content_hash") or self.generate_content_hash(
                existing.get("title", ""), existing.get("description", "")
            )
            if new_hash == existing_hash:
                return True, "Duplicate Content Hash match"

            # 3. Fuzzy Text Similarity Check
            existing_title = existing.get("title", "")
            similarity = fuzz.ratio(new_title.lower(), existing_title.lower())
            if similarity >= self.similarity_threshold:
                return True, f"Fuzzy similarity match ({similarity:.1f}%)"

        return False, None