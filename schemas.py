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

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: UUID

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