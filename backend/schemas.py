
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# SOURCE SCHEMAS
# ============================================================

class SourceBase(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    scraping_type: Optional[str] = None
    scraping_rules: Optional[Dict[str, Any]] = None
    frequency_minutes: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    base_url: Optional[str] = Field(default=None, min_length=1)
    scraping_type: Optional[str] = None
    scraping_rules: Optional[Dict[str, Any]] = None
    frequency_minutes: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    id: UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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
    category: Optional[str] = None
    confidence_score: Optional[float] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    original_url: Optional[str] = Field(default=None, min_length=1)
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
    category: Optional[str] = None
    confidence_score: Optional[float] = None


class ProjectResponse(ProjectBase):
    id: UUID
    is_duplicate: Optional[bool] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# KEYWORD SCHEMAS
# ============================================================

class KeywordBase(BaseModel):
    keyword: str = Field(min_length=1)
    category: Optional[str] = None
    is_active: Optional[bool] = True


class KeywordCreate(KeywordBase):
    pass


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = None
    is_active: Optional[bool] = None


class KeywordResponse(KeywordBase):
    id: UUID
    keyword: str = Field(validation_alias="phrase")
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)