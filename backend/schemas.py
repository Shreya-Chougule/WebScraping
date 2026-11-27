
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


# ============================================================
# USER & AUTH SCHEMAS
# ============================================================

class ManualTruelancerFetchRequest(BaseModel):
    max_pages: Optional[int] = Field(default=None, ge=1, le=20)
    min_request_interval: Optional[float] = Field(default=None, ge=0.0, le=60.0)
    provider: Optional[Literal["direct", "scraperapi"]] = None


class ManualTruelancerFetchResponse(BaseModel):
    run_id: str
    source_id: str
    source_name: str
    provider: str
    start_url: str
    status: str
    records_found: int
    inserted: int
    duplicate_skipped: int
    irrelevant_skipped: int
    missing_url_skipped: int
    invalid_skipped: int
    failed: int
    submission: Dict[str, Any]


# ============================================================
# RECURRING SCHEDULE SCHEMAS
# ============================================================

class ScheduleBase(BaseModel):
    source_id: UUID
    name: str = Field(min_length=1, max_length=120)
    frequency: Literal["daily", "weekly", "monthly", "custom"]
    time_of_day: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    weekdays: Optional[List[int]] = None
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=43200)
    timezone: str = Field(default="Asia/Kolkata", min_length=1)
    max_pages: int = Field(default=3, ge=1, le=20)
    min_request_interval: float = Field(default=1.0, ge=0.0, le=60.0)
    is_enabled: bool = True


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    source_id: Optional[UUID] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    frequency: Optional[Literal["daily", "weekly", "monthly", "custom"]] = None
    time_of_day: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    weekdays: Optional[List[int]] = None
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=43200)
    timezone: Optional[str] = Field(default=None, min_length=1)
    max_pages: Optional[int] = Field(default=None, ge=1, le=20)
    min_request_interval: Optional[float] = Field(default=None, ge=0.0, le=60.0)
    is_enabled: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    id: UUID
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_error: Optional[str] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class UserRegister(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "viewer"]



class UserResponse(BaseModel):
    id: str
    email: str
    role: str = "viewer"
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================
# NOTIFICATION SCHEMAS
# ============================================================

class NotificationCreate(BaseModel):
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    type: Literal["info", "success", "warning", "high_priority"] = "info"
    user_id: Optional[str] = None
    link: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: str = "info"
    is_read: bool = False
    user_id: Optional[str] = None
    link: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total: int
