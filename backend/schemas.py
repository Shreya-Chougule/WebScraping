from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# SOURCE SCHEMAS
# ============================================================

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


# ============================================================
# PROJECT SCHEMAS
# ============================================================

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


# ============================================================
# KEYWORD SCHEMAS
# ============================================================

class KeywordBase(BaseModel):
    keyword: str


class KeywordCreate(KeywordBase):
    pass


class KeywordResponse(KeywordBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# SCRAPING RUN SCHEMAS
# ============================================================

class ScrapingRunCreate(BaseModel):
    source_id: UUID
    status: Literal["RUNNING"] = "RUNNING"


class ScrapingRunUpdate(BaseModel):
    status: Literal["SUCCESS", "FAILED"]
    records_found: int = Field(default=0, ge=0)
    error_log: Optional[str] = None


class ScrapingRunResponse(BaseModel):
    id: UUID
    source_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[str] = None
    records_found: Optional[int] = 0
    error_log: Optional[str] = None

    class Config:
        from_attributes = True