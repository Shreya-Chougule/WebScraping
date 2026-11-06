
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# --- Source Schemas ---

class SourceBase(BaseModel):
    name: str
    base_url: str


class SourceCreate(SourceBase):
    pass


class SourceResponse(SourceBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Project Schemas ---

class ProjectBase(BaseModel):
    title: str
    original_url: str
    description: Optional[str] = None
    source_id: Optional[UUID] = None

    project_type: Optional[str] = None
    required_technologies: Optional[List[str]] = None

    client_name: Optional[str] = None
    location: Optional[str] = None

    budget: Optional[str] = None
    currency: Optional[str] = None

    posted_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

    contact_info: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: UUID

    # Classification and duplicate-detection fields
    category: Optional[str] = None
    confidence_score: Optional[float] = None
    is_duplicate: Optional[bool] = None

    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Keyword Schemas ---

class KeywordBase(BaseModel):
    keyword: str


class KeywordCreate(KeywordBase):
    pass


class KeywordResponse(KeywordBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
