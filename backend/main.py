
import os
import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta, date, time
from typing import List, Optional
from uuid import UUID
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.openapi.utils import get_openapi
from backend.supabase_client import create_client, Client


logger = logging.getLogger("scrapescout.api")

try:
    from backend.schemas import (
        ProjectCreate,
        ProjectUpdate,
        ProjectResponse,
        SourceCreate,
        SourceUpdate,
        SourceResponse,
        KeywordCreate,
        KeywordUpdate,
        KeywordResponse,
        ScrapingRunCreate,
        ScrapingRunUpdate,
        ScrapingRunResponse,
        ManualTruelancerFetchRequest,
        ManualTruelancerFetchResponse,
        ScheduleCreate,
        ScheduleUpdate,
        ScheduleResponse,
        UserLogin,
        UserRegister,
        UserResponse,
        TokenResponse,
        NotificationCreate,
        NotificationResponse,
        NotificationListResponse,
    )
    from backend.auth import (
        CurrentUser,
        create_access_token,
        decode_access_token,
        get_current_user,
        require_admin,
        require_authenticated,
        hash_password,
        verify_password,
        get_local_user,
        add_local_user,
    )
    from backend.notifications import (
        create_notification,
        list_notifications,
        mark_as_read,
        mark_all_as_read,
        safe_notify,
    )
    from backend.security import (
        is_rate_limited,
        sanitize_csv_cell,
    )
    from backend.export_utils import (
        generate_projects_xlsx,
        get_export_filename,
    )
except ImportError:
    from schemas import (
        ProjectCreate,
        ProjectUpdate,
        ProjectResponse,
        SourceCreate,
        SourceUpdate,
        SourceResponse,
        KeywordCreate,
        KeywordUpdate,
        KeywordResponse,
        ScrapingRunCreate,
        ScrapingRunUpdate,
        ScrapingRunResponse,
        ManualTruelancerFetchRequest,
        ManualTruelancerFetchResponse,
        ScheduleCreate,
        ScheduleUpdate,
        ScheduleResponse,
        UserLogin,
        UserRegister,
        UserResponse,
        TokenResponse,
        NotificationCreate,
        NotificationResponse,
        NotificationListResponse,
    )
    from auth import (
        CurrentUser,
        create_access_token,
        decode_access_token,
        get_current_user,
        require_admin,
        require_authenticated,
        hash_password,
        verify_password,
        get_local_user,
        add_local_user,
    )
    from notifications import (
        create_notification,
        list_notifications,
        mark_as_read,
        mark_all_as_read,
        safe_notify,
    )
    from security import (
        is_rate_limited,
        sanitize_csv_cell,
    )
    from export_utils import (
        generate_projects_xlsx,
        get_export_filename,
    )


try:
    from backend.route_security import ProductionAuthMiddleware, PUBLIC_PATHS
except ImportError:
    from route_security import ProductionAuthMiddleware, PUBLIC_PATHS

import sys
from pathlib import Path

# Ensure backend directory is in sys.path so 'src' can always be resolved
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from src.scheduler import (
        start_scheduler_from_config,
        stop_scheduler,
        get_scheduler,
        build_trigger_for_schedule,
        calculate_next_run_time,
        is_scheduler_enabled_in_env,
        sync_schedules_to_scheduler,
    )
    from src.pipeline import run_truelancer_pipeline
    from src.deduplicator import ProjectDeduplicator
    from src.supabase_mapper import map_project_to_supabase
    from src.scraper import ScrapingAccessError
    from src.scraperapi_provider import (
        ScraperAPIAccessError,
        ScraperAPIConfigError,
        ScraperAPIError,
        redact_api_key,
    )
except ImportError:
    try:
        from backend.src.scheduler import start_scheduler_from_config, stop_scheduler
        from backend.src.pipeline import run_truelancer_pipeline
        from backend.src.deduplicator import ProjectDeduplicator
        from backend.src.supabase_mapper import map_project_to_supabase
        from backend.src.scraper import ScrapingAccessError
        from backend.src.scraperapi_provider import (
            ScraperAPIAccessError,
            ScraperAPIConfigError,
            ScraperAPIError,
            redact_api_key,
        )
    except ImportError:
        from scheduler import start_scheduler_from_config, stop_scheduler
        from pipeline import run_truelancer_pipeline
        from deduplicator import ProjectDeduplicator
        from supabase_mapper import map_project_to_supabase
        from scraper import ScrapingAccessError
        from scraperapi_provider import (
            ScraperAPIAccessError,
            ScraperAPIConfigError,
            ScraperAPIError,
            redact_api_key,
        )

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize scheduler; propagate any exception so FastAPI startup fails when configuration is invalid
    start_scheduler_from_config()

    if is_scheduler_enabled_in_env():
        try:
            _sync_persisted_schedules()
        except Exception as exc:
            logger.warning("Could not load persisted schedules on startup: %s", exc)

    yield

    # Shutdown: Stop the scheduler safely without blocking web server termination
    try:
        stop_scheduler(wait=False)
    except Exception as exc:
        logger.error("Error stopping automated scraping scheduler: %s", exc)


app = FastAPI(title="Project Discovery Tool API", lifespan=lifespan)

# SCRAPESCOUT_SWAGGER_BEARER_AUTH
# Document the existing middleware-based JWT authentication in Swagger.
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault(
        "securitySchemes", {}
    )["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your backend JWT access token.",
    }

    http_methods = {
        "get", "post", "put", "patch", "delete",
        "options", "head", "trace",
    }

    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in http_methods:
                continue

            if path in PUBLIC_PATHS:
                operation["security"] = []
            else:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================
app.add_middleware(
    ProductionAuthMiddleware,
    auth_validator=get_current_user,
)
# CORS CONFIGURATION
# ============================================================

# Set FRONTEND_ORIGINS as a comma-separated list of trusted frontend
# origins in production. Local React development URLs are the defaults.
FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in FRONTEND_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GENERAL ENDPOINTS
# ============================================================

@app.get("/")
def read_root():
    return {
        "message": "Project Discovery Tool Backend is Running!"
    }


@app.get("/test-db")
def test_db_connection():
    """
    Test database connectivity.
    Returns only a safe connectivity status without returning actual project records
    or sensitive database contents.
    """
    try:
        response = (
            supabase.table("projects")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "status": "success",
            "message": "Database connection healthy.",
            "connected": True,
        }

    except Exception:
        logger.exception("Unexpected API/database error")
        return {
            "status": "error",
            "message": "Database connection failed.",
            "connected": False,
        }


# ============================================================
# AUTHENTICATION & ACCESS CONTROL ENDPOINTS (PHASE 14)
# ============================================================

@app.post(
    "/auth/login",
    response_model=TokenResponse,
)
def login(credentials: UserLogin, request: Request):
    """
    Authenticate a user via Supabase Auth or local store.
    Issues a secure JWT access token with role permissions.
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip, bucket="auth", limit=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again shortly.",
        )

    email = credentials.email.strip().lower()
    password = credentials.password

    user_info = None
    access_token = None

    # 1. Attempt Supabase Auth login
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        if auth_response and auth_response.user:
            sb_user = auth_response.user
            user_id = str(sb_user.id)
            user_meta = getattr(sb_user, "user_metadata", {}) or {}
            full_name = user_meta.get("full_name") or email.split("@")[0].title()
            role = "viewer"

            try:
                user_record = supabase.table("users").select("*").eq("id", user_id).execute()
                if user_record.data:
                    database_role = user_record.data[0].get("role")
                    if database_role in ("admin", "viewer"):
                        role = database_role
                    full_name = user_record.data[0].get("full_name", full_name)
            except Exception:
                pass

            user_info = {
                "id": user_id,
                "email": email,
                "role": role,
                "full_name": full_name,
            }
    except Exception as exc:
        logger.debug("Supabase sign in failed or unavailable: %s", exc)

    # 2. Local accounts fallback (development, tests, demo)
    if not user_info:
        local_user = get_local_user(email)
        if local_user and verify_password(password, local_user["password_hash"]):
            user_info = {
                "id": local_user["id"],
                "email": local_user["email"],
                "role": local_user["role"],
                "full_name": local_user.get("full_name", ""),
            }

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Consistently issue backend JWT access token signed with get_jwt_secret()
    access_token = create_access_token({
        "sub": user_info["id"],
        "email": user_info["email"],
        "role": user_info["role"],
        "full_name": user_info.get("full_name"),
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info,
    }


@app.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: UserRegister, request: Request):
    """
    Register a new user account with role assignment (default: viewer).
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip, bucket="auth", limit=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again shortly.",
        )

    email = user_data.email.strip().lower()
    password = user_data.password
    role = "viewer"
    full_name = user_data.full_name or email.split("@")[0].title()

    if get_local_user(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user_info = None
    access_token = None

    # 1. Attempt Supabase Auth registration
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "role": role,
                }
            }
        })
        if auth_response and auth_response.user:
            sb_user = auth_response.user
            user_id = str(sb_user.id)
            user_info = {
                "id": user_id,
                "email": email,
                "role": role,
                "full_name": full_name,
            }
            try:
                supabase.table("users").insert({
                    "id": user_id,
                    "email": email,
                    "role": role,
                    "full_name": full_name,
                }).execute()
            except Exception:
                pass
    except Exception as exc:
        logger.debug("Supabase sign up failed or unavailable: %s", exc)

    # 2. Local fallback registration
    if not user_info:
        local_record = add_local_user(
            email=email,
            password=password,
            role=role,
            full_name=full_name,
        )
        user_info = {
            "id": local_record["id"],
            "email": local_record["email"],
            "role": local_record["role"],
            "full_name": local_record["full_name"],
        }

    # Consistently issue backend JWT access token signed with get_jwt_secret()
    access_token = create_access_token({
        "sub": user_info["id"],
        "email": user_info["email"],
        "role": user_info["role"],
        "full_name": user_info["full_name"],
    })

    safe_notify(
        title="New User Registered",
        message=f"User {email} joined as {role}.",
        notif_type="info",
        client=supabase,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info,
    }


@app.get(
    "/auth/me",
    response_model=UserResponse,
)
def get_my_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Retrieve currently authenticated user profile and permissions."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
    }


@app.post("/auth/logout")
def logout(current_user: CurrentUser = Depends(get_current_user)):
    """Log out the current session."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return {"message": "Successfully logged out."}


@app.get(
    "/users",
    response_model=List[UserResponse],
)
def list_users_endpoint(current_user: CurrentUser = Depends(require_admin)):
    """Admin endpoint to list system users."""
    try:
        response = supabase.table("users").select("*").execute()
        if response.data:
            return response.data
    except Exception:
        pass
    try:
        from backend.auth import _local_users
    except ImportError:
        from auth import _local_users
    return [
        {
            "id": u["id"],
            "email": u["email"],
            "role": u["role"],
            "full_name": u.get("full_name"),
            "created_at": None,
        }
        for u in _local_users.values()
    ]


# ============================================================
# PROJECT ENDPOINTS
# ============================================================

@app.get(
    "/projects",
    response_model=List[ProjectResponse],
)
def get_projects():
    """Return all projects, fetching records in batches."""
    try:
        projects = []
        page_size = 1000
        offset = 0

        while True:
            response = (
                supabase.table("projects")
                .select("*")
                .range(offset, offset + page_size - 1)
                .execute()
            )

            batch = response.data or []
            projects.extend(batch)

            if len(batch) < page_size:
                break

            offset += page_size

        return projects

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch projects due to a server error.",
        )


def escape_postgrest_search(value: str) -> str:
    """Escape characters that interfere with PostgREST filter parsing."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


@app.get(
    "/projects/search",
    response_model=List[ProjectResponse],
)
def search_projects(
    search: Optional[str] = None,
    project_type: Optional[str] = None,
    technology: Optional[str] = None,
    location: Optional[str] = None,
    source_id: Optional[UUID] = None,
    category: Optional[str] = None,
    posted_from: Optional[datetime] = None,
    posted_to: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Search, filter, and paginate projects."""
    if posted_from and posted_to and posted_from > posted_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="posted_from cannot be later than posted_to.",
        )

    try:
        query = supabase.table("projects").select("*")

        if search and search.strip():
            search_value = escape_postgrest_search(search.strip())
            query = query.or_(
                f'title.ilike."%{search_value}%",'
                f'description.ilike."%{search_value}%"'
            )

        if project_type:
            query = query.eq("project_type", project_type)

        if technology:
            query = query.contains(
                "required_technologies",
                [technology],
            )

        if location and location.strip():
            query = query.ilike(
                "location",
                f"%{location.strip()}%",
            )

        if source_id:
            query = query.eq("source_id", str(source_id))

        if category:
            query = query.eq("category", category)

        if posted_from:
            query = query.gte(
                "posted_date",
                posted_from.isoformat(),
            )

        if posted_to:
            query = query.lte(
                "posted_date",
                posted_to.isoformat(),
            )

        query = query.range(offset, offset + limit - 1)
        response = query.execute()

        return response.data or []

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to search projects due to a server error.",
        )


# ============================================================
# PROJECT CSV EXPORT
# ============================================================

@app.get("/projects/export")
def export_projects_csv(
    search: Optional[str] = None,
    project_type: Optional[str] = None,
    technology: Optional[str] = None,
    location: Optional[str] = None,
    source_id: Optional[UUID] = None,
    category: Optional[str] = None,
    posted_from: Optional[datetime] = None,
    posted_to: Optional[datetime] = None,
    format: str = Query(
        default="csv",
        description="Export format: 'csv' or 'excel'/'xlsx'",
    ),
):
    """Export matching projects from Supabase as a downloadable CSV or Excel spreadsheet."""

    if format.lower() not in ("csv", "excel", "xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported export format. Supported formats are 'csv' and 'excel'.",
        )

    if posted_from and posted_to and posted_from > posted_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="posted_from cannot be later than posted_to.",
        )

    columns = [
        "id",
        "source_id",
        "title",
        "description",
        "project_type",
        "required_technologies",
        "client_name",
        "location",
        "budget",
        "currency",
        "posted_date",
        "deadline",
        "original_url",
        "contact_info",
        "category",
        "confidence_score",
        "is_duplicate",
        "created_at",
    ]

    try:
        query = supabase.table("projects").select("*")

        if search and search.strip():
            search_value = escape_postgrest_search(search.strip())
            query = query.or_(
                f'title.ilike."%{search_value}%",'
                f'description.ilike."%{search_value}%"'
            )

        if project_type:
            query = query.eq("project_type", project_type)

        if technology:
            query = query.contains(
                "required_technologies",
                [technology],
            )

        if location and location.strip():
            query = query.ilike(
                "location",
                f"%{location.strip()}%",
            )

        if source_id:
            query = query.eq("source_id", str(source_id))

        if category:
            query = query.eq("category", category)

        if posted_from:
            query = query.gte(
                "posted_date",
                posted_from.isoformat(),
            )

        if posted_to:
            query = query.lte(
                "posted_date",
                posted_to.isoformat(),
            )

        # Fetch in batches to avoid the usual 1,000-row API limit.
        projects = []
        page_size = 1000
        offset = 0

        while True:
            response = query.range(
                offset,
                offset + page_size - 1,
            ).execute()

            batch = response.data or []
            projects.extend(batch)

            if len(batch) < page_size:
                break

            offset += page_size

        if format.lower() in ("excel", "xlsx"):
            xlsx_content = generate_projects_xlsx(columns, projects)
            return StreamingResponse(
                iter([xlsx_content]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": 'attachment; filename="scrapescout_projects.xlsx"'
                },
            )

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()

        for project in projects:
            row = {}

            for column in columns:
                value = sanitize_csv_cell(project.get(column))
                row[column] = value

            writer.writerow(row)

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    'attachment; filename="scrapescout_projects.csv"'
                )
            },
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export projects due to a server error.",
        )


@app.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
def get_project(project_id: UUID):
    """Retrieve one project using its UUID."""
    try:
        response = (
            supabase.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project was not found.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch the project due to a server error.",
        )


@app.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        project_data = project.model_dump(
            mode="json",
            exclude_none=True,
        )

        response = (
            supabase.table("projects")
            .insert(project_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Project insertion returned no data.",
            )

        new_project_record = response.data[0]
        try:
            safe_notify(
                title="New Project Discovered",
                message=f"Opportunity '{project.title}' was added to ScrapeScout.",
                notif_type="info",
                link=project.original_url,
                client=supabase,
            )
        except Exception:
            pass

        return new_project_record

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected API/database error")
        error_msg = str(exc)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with this unique value already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the project due to a server error.",
        )


@app.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
def update_project(
    project_id: UUID,
    project: ProjectUpdate,
):
    """Partially update an existing project."""
    update_data = project.model_dump(
        mode="json",
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    if (
        ("title" in update_data and update_data["title"] is None)
        or (
            "original_url" in update_data
            and update_data["original_url"] is None
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project title and original URL cannot be null.",
        )

    try:
        response = (
            supabase.table("projects")
            .update(update_data)
            .eq("id", str(project_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project was not found.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected API/database error")
        error_msg = str(exc)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with this unique value already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the project due to a server error.",
        )


@app.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: str,
    current_user: CurrentUser = Depends(require_admin),
):
    """Delete a project (Admin only)."""
    try:
        (
            supabase.table("projects")
            .delete()
            .eq("id", project_id)
            .execute()
        )

        return None

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete the project due to a server error.",
        )


# ============================================================
# SOURCE ENDPOINTS
# ============================================================

@app.get(
    "/sources",
    response_model=List[SourceResponse],
)
def get_sources(is_active: Optional[bool] = None):
    """Retrieve sources with an optional active-status filter."""
    try:
        query = supabase.table("sources").select("*")

        if is_active is not None:
            query = query.eq("is_active", is_active)

        response = query.execute()
        return response.data or []

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch sources due to a server error.",
        )


@app.post(
    "/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source(source: SourceCreate):
    """Create a source with its scraping configuration."""
    try:
        source_data = source.model_dump(
            mode="json",
            exclude_none=True,
        )

        response = (
            supabase.table("sources")
            .insert(source_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Source insertion returned no data.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected API/database error")
        error_msg = str(exc)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This source already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the source due to a server error.",
        )


@app.patch(
    "/sources/{source_id}",
    response_model=SourceResponse,
)
def update_source(source_id: UUID, source: SourceUpdate):
    """Partially update source details or scraping configuration."""
    update_data = source.model_dump(
        mode="json",
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    if (
        ("name" in update_data and update_data["name"] is None)
        or ("base_url" in update_data and update_data["base_url"] is None)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source name and base URL cannot be null.",
        )

    try:
        response = (
            supabase.table("sources")
            .update(update_data)
            .eq("id", str(source_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source was not found.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the source due to a server error.",
        )


# ============================================================
# KEYWORD ENDPOINTS
# ============================================================

@app.get(
    "/keywords",
    response_model=List[KeywordResponse],
)
def get_keywords():
    """Retrieve all configured keywords."""
    try:
        response = (
            supabase.table("keywords")
            .select("*")
            .execute()
        )

        return response.data or []

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch keywords due to a server error.",
        )


@app.post(
    "/keywords",
    response_model=KeywordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_keyword(keyword: KeywordCreate):
    """Create a keyword, mapping API keyword to database phrase."""
    try:
        keyword_data = keyword.model_dump(
            mode="json",
            exclude_none=True,
        )

        database_data = {
            "phrase": keyword_data["keyword"],
            "category": keyword_data.get("category"),
            "is_active": keyword_data.get("is_active", True),
        }

        response = (
            supabase.table("keywords")
            .insert(database_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Keyword insertion returned no data.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected API/database error")
        error_msg = str(exc)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This keyword already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the keyword due to a server error.",
        )


@app.patch(
    "/keywords/{keyword_id}",
    response_model=KeywordResponse,
)
def update_keyword(
    keyword_id: UUID,
    keyword: KeywordUpdate,
):
    """Partially update a keyword."""
    update_data = keyword.model_dump(
        mode="json",
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided.",
        )

    if "keyword" in update_data:
        if update_data["keyword"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Keyword cannot be null.",
            )

        update_data["phrase"] = update_data.pop("keyword")

    try:
        response = (
            supabase.table("keywords")
            .update(update_data)
            .eq("id", str(keyword_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword was not found.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected API/database error")
        error_msg = str(exc)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This keyword already exists.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the keyword due to a server error.",
        )


@app.delete(
    "/keywords/{keyword_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_keyword(keyword_id: UUID):
    """Delete a keyword by its UUID."""
    try:
        response = (
            supabase.table("keywords")
            .delete()
            .eq("id", str(keyword_id))
            .select("id")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword was not found.",
            )

        return None

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete the keyword due to a server error.",
        )


# ============================================================
# DASHBOARD ANALYTICS ENDPOINT
# ============================================================

@app.get("/analytics/dashboard")
def get_dashboard_analytics():
    """Return dashboard statistics using Supabase exact-count queries."""
    try:
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist_offset)

        today_start_ist = now_ist.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        today_start_utc = today_start_ist.astimezone(timezone.utc)

        tomorrow_start_ist = today_start_ist + timedelta(days=1)
        tomorrow_start_utc = tomorrow_start_ist.astimezone(timezone.utc)

        total_response = (
            supabase.table("projects")
            .select("id", count="exact")
            .execute()
        )

        total_projects = total_response.count or 0

        today_response = (
            supabase.table("projects")
            .select("id", count="exact")
            .gte("created_at", today_start_utc.isoformat())
            .lt("created_at", tomorrow_start_utc.isoformat())
            .execute()
        )

        projects_today = today_response.count or 0

        today_duplicates_count = 0
        try:
            today_dup_response = (
                supabase.table("projects")
                .select("id", count="exact")
                .eq("is_duplicate", True)
                .gte("created_at", today_start_utc.isoformat())
                .lt("created_at", tomorrow_start_utc.isoformat())
                .execute()
            )
            today_duplicates_count = today_dup_response.count or 0
        except Exception:
            today_duplicates_count = 0

        inserted_today = max(0, projects_today - today_duplicates_count)

        duplicates_skipped = 0
        try:
            dup_response = (
                supabase.table("projects")
                .select("id", count="exact")
                .eq("is_duplicate", True)
                .execute()
            )
            duplicates_skipped = dup_response.count or 0
        except Exception:
            duplicates_skipped = 0

        project_types = ["Web", "Mobile", "Both", "Unspecified"]
        projects_by_type = {}

        for project_type in project_types:
            type_response = (
                supabase.table("projects")
                .select("id", count="exact")
                .eq("project_type", project_type)
                .execute()
            )

            projects_by_type[project_type] = type_response.count or 0

        sources_response = (
            supabase.table("sources")
            .select("id,name,is_active")
            .eq("is_active", True)
            .execute()
        )

        projects_by_source = []

        for source in sources_response.data or []:
            if source.get("is_active") is False:
                continue

            source_id = source.get("id")
            source_name = source.get("name", "Unknown")

            if not source_id:
                continue

            source_projects_response = (
                supabase.table("projects")
                .select("id", count="exact")
                .eq("source_id", source_id)
                .execute()
            )

            projects_by_source.append({
                "source_name": source_name,
                "project_count": source_projects_response.count or 0,
            })

        # Count every scraping run, including unexpected statuses.
        total_runs_response = (
            supabase.table("scraping_runs")
            .select("id", count="exact")
            .execute()
        )

        scraping_runs = {
            "total": total_runs_response.count or 0,
            "successful": 0,
            "failed": 0,
            "running": 0,
        }

        status_keys = {
            "SUCCESS": "successful",
            "FAILED": "failed",
            "RUNNING": "running",
        }

        for run_status, result_key in status_keys.items():
            run_response = (
                supabase.table("scraping_runs")
                .select("id", count="exact")
                .eq("status", run_status)
                .execute()
            )

            scraping_runs[result_key] = run_response.count or 0

        upcoming_schedules = []
        try:
            sched_response = (
                supabase.table("scraping_schedules")
                .select("*")
                .eq("is_enabled", True)
                .execute()
            )
            for sched in sched_response.data or []:
                if not isinstance(sched, dict) or not sched.get("is_enabled", True):
                    continue
                try:
                    next_dt = calculate_next_run_time(sched)
                except Exception:
                    next_dt = None
                upcoming_schedules.append({
                    "id": str(sched.get("id")),
                    "name": sched.get("name"),
                    "source_id": str(sched.get("source_id")),
                    "frequency": sched.get("frequency"),
                    "timezone": sched.get("timezone") or "Asia/Kolkata",
                    "next_run_at": next_dt.isoformat() if next_dt else sched.get("next_run_at"),
                    "last_run_at": sched.get("last_run_at"),
                    "last_run_status": sched.get("last_run_status"),
                })
            upcoming_schedules.sort(
                key=lambda item: item.get("next_run_at") or "9999"
            )
        except Exception:
            upcoming_schedules = []

        return {
            "total_projects": total_projects,
            "projects_today": projects_today,
            "inserted_today": inserted_today,
            "duplicates_skipped": duplicates_skipped,
            "active_sources_count": len(projects_by_source),
            "projects_by_type": projects_by_type,
            "projects_by_source": projects_by_source,
            "scraping_runs": scraping_runs,
            "scheduler_enabled": is_scheduler_enabled_in_env(),
            "upcoming_schedules": upcoming_schedules,
        }

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch dashboard analytics due to a server error.",
        )


# ============================================================
# DAILY PROJECT COMPILATION
# ============================================================

@app.get("/analytics/daily-opportunities")
def get_daily_opportunities(
    target_date: Optional[date] = Query(
        default=None,
        alias="date",
        description="Compilation date in Asia/Kolkata (YYYY-MM-DD). Defaults to today.",
    ),
):
    """
    Return the consolidated list of relevant, non-duplicate projects
    discovered during one calendar day in Asia/Kolkata.

    Historical daily lists are reconstructed from projects.created_at.
    Projects submitted through the scraping pipeline have already passed
    relevance classification before being stored.
    """
    ist_timezone = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_timezone)
    selected_date = target_date or now_ist.date()

    start_ist = datetime.combine(
        selected_date,
        time.min,
        tzinfo=ist_timezone,
    )
    end_ist = start_ist + timedelta(days=1)

    start_utc = start_ist.astimezone(timezone.utc)
    end_utc = end_ist.astimezone(timezone.utc)

    try:
        query = (
            supabase.table("projects")
            .select("*")
            .gte("created_at", start_utc.isoformat())
            .lt("created_at", end_utc.isoformat())
            .or_("is_duplicate.is.null,is_duplicate.eq.false")
            .order("created_at", desc=True)
            .order("id", desc=False)
        )

        projects = []
        page_size = 1000
        offset = 0

        while True:
            response = query.range(
                offset,
                offset + page_size - 1,
            ).execute()

            batch = response.data or []
            projects.extend(batch)

            if len(batch) < page_size:
                break

            offset += page_size

        is_today = selected_date == now_ist.date()

        return {
            "title": (
                "Today's Project Opportunities"
                if is_today
                else f"Project Opportunities for {selected_date.isoformat()}"
            ),
            "date": selected_date.isoformat(),
            "timezone": "Asia/Kolkata",
            "total_projects": len(projects),
            "is_historical": not is_today,
            "projects": projects,
        }

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to compile daily project opportunities due to a server error.",
        )


# ============================================================
# SCRAPING RUN ENDPOINTS
# ============================================================

@app.get(
    "/scraping-runs",
    response_model=List[ScrapingRunResponse],
)
def get_scraping_runs(
    source_id: Optional[UUID] = None,
    run_status: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(RUNNING|SUCCESS|FAILED)$",
    ),
    started_from: Optional[datetime] = None,
    started_to: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve scraping-run history with filters and pagination."""
    if started_from and started_to and started_from > started_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="started_from cannot be later than started_to.",
        )

    try:
        query = supabase.table("scraping_runs").select("*")

        if source_id is not None:
            query = query.eq("source_id", str(source_id))

        if run_status is not None:
            query = query.eq("status", run_status)

        if started_from is not None:
            query = query.gte(
                "started_at",
                started_from.isoformat(),
            )

        if started_to is not None:
            query = query.lte(
                "started_at",
                started_to.isoformat(),
            )

        query = query.order("started_at", desc=True)
        query = query.range(offset, offset + limit - 1)

        response = query.execute()
        return response.data or []

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch scraping runs due to a server error.",
        )


@app.post(
    "/scraping-runs",
    response_model=ScrapingRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scraping_run_endpoint(scraping_run: ScrapingRunCreate):
    """Create a scraping-run record with RUNNING status."""
    try:
        run_data = scraping_run.model_dump(
            mode="json",
            exclude_none=True,
        )

        response = (
            supabase.table("scraping_runs")
            .insert(run_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Scraping-run insertion returned no data.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the scraping run due to a server error.",
        )


@app.patch(
    "/scraping-runs/{run_id}",
    response_model=ScrapingRunResponse,
)
def update_scraping_run_endpoint(
    run_id: UUID,
    scraping_run: ScrapingRunUpdate,
):
    """Complete a scraping run with SUCCESS or FAILED status."""
    try:
        update_data = scraping_run.model_dump(
            mode="json",
            exclude_none=False,
        )

        update_data["completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        response = (
            supabase.table("scraping_runs")
            .update(update_data)
            .eq("id", str(run_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scraping run was not found.",
            )

        updated_run = response.data[0]
        try:
            status_val = update_data.get("status", "UPDATED")
            safe_notify(
                title=f"Scraping Run {status_val.capitalize()}",
                message=f"Scraping job completed with status {status_val}. {update_data.get('records_found', 0)} records found.",
                notif_type="success" if status_val == "SUCCESS" else "warning",
                client=supabase,
            )
        except Exception:
            pass

        return updated_run

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected API/database error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the scraping run due to a server error.",
        )


# ============================================================
# NOTIFICATION ENDPOINTS (PHASE 15)
# ============================================================

@app.get(
    "/notifications",
    response_model=NotificationListResponse,
)
def get_user_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieve notifications for the current user and system broadcasts."""
    return list_notifications(
        user_id=current_user.id,
        role=current_user.role,
        unread_only=unread_only,
        limit=limit,
        client=supabase,
    )


@app.patch("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mark a specific notification as read."""
    success = mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
        client=supabase,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return {"status": "success", "id": notification_id}


@app.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mark all unread notifications as read."""
    marked_count = mark_all_as_read(
        user_id=current_user.id,
        client=supabase,
    )
    return {"status": "success", "marked_read": marked_count}


@app.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_system_notification(
    notification: NotificationCreate,
    current_user: CurrentUser = Depends(require_admin),
):
    """Admin endpoint to create a manual or broadcast notification."""
    return create_notification(
        title=notification.title,
        message=notification.message,
        notif_type=notification.type,
        user_id=notification.user_id,
        link=notification.link,
        client=supabase,
    )


# ============================================================
# MANUAL SCRAPING ENDPOINTS
# ============================================================

def _resolve_truelancer_start_url(source: dict) -> str:
    """Resolve the Truelancer listing URL from source config or environment."""
    rules = source.get("scraping_rules")
    if isinstance(rules, dict):
        rule_url = rules.get("start_url")
        if isinstance(rule_url, str) and rule_url.strip():
            return rule_url.strip()

    base_url = (source.get("base_url") or "").strip().rstrip("/")
    if base_url:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.path and parsed.path != "/":
            return base_url

    env_url = os.getenv("SCHEDULER_START_URL", "").strip()
    if env_url:
        return env_url

    if base_url:
        return f"{base_url}/freelance-jobs"

    return "https://www.truelancer.com/freelance-jobs"


def _backend_create_scraping_run(source_id: str, api_endpoint: str = "") -> str:
    """Create a RUNNING scraping run record directly in Supabase."""
    response = (
        supabase.table("scraping_runs")
        .insert({"source_id": source_id, "status": "RUNNING"})
        .execute()
    )
    if not response.data or not response.data[0].get("id"):
        raise RuntimeError("Failed to create scraping_runs record.")
    return str(response.data[0]["id"])


def _backend_update_scraping_run(
    run_id: str,
    status: str,
    records_found: int,
    error_log: Optional[str] = None,
    api_endpoint: str = "",
) -> None:
    """Update a scraping run record directly in Supabase and emit notification."""
    update_payload = {
        "status": status,
        "records_found": records_found,
        "error_log": error_log,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    (
        supabase.table("scraping_runs")
        .update(update_payload)
        .eq("id", str(run_id))
        .execute()
    )
    try:
        safe_notify(
            title=f"Scraping Run {status.capitalize()}",
            message=f"Truelancer manual fetch completed with status {status}. {records_found} records found.",
            notif_type="success" if status == "SUCCESS" else "warning",
            client=supabase,
        )
    except Exception:
        pass


def _backend_submit_projects(projects: list, source_id: str) -> dict:
    """Validate, deduplicate, insert projects, and retain failure diagnostics."""
    results = {
        "total": len(projects),
        "inserted": 0,
        "duplicate_skipped": 0,
        "irrelevant_skipped": 0,
        "missing_url_skipped": 0,
        "source_not_found_skipped": 0,
        "invalid_skipped": 0,
        "failed": 0,
        "failure_details": [],
    }

    def record_failure(project, reason: str) -> None:
        if len(results["failure_details"]) >= 10:
            return

        title = str(getattr(project, "title", None) or "Untitled project")
        results["failure_details"].append({
            "title": title[:160],
            "error": str(reason)[:500],
        })

    if not projects:
        return results

    existing_response = (
        supabase.table("projects")
        .select("id,title,description,original_url")
        .execute()
    )
    existing_projects = list(existing_response.data or [])
    deduplicator = ProjectDeduplicator()

    for project in projects:
        if not getattr(project, "is_relevant", False):
            results["irrelevant_skipped"] += 1
            continue

        original_url = getattr(project, "original_url", None)
        if (
            not isinstance(original_url, str)
            or not original_url.strip()
            or original_url.strip() == "Not specified"
        ):
            results["missing_url_skipped"] += 1
            continue

        try:
            payload = map_project_to_supabase(project, source_id)
        except ValueError as exc:
            results["invalid_skipped"] += 1
            logger.warning(
                "Invalid project mapping for '%s': %s",
                getattr(project, "title", ""),
                exc,
            )
            continue

        is_duplicate, _ = deduplicator.is_duplicate(
            payload,
            existing_projects,
        )
        if is_duplicate:
            results["duplicate_skipped"] += 1
            continue

        try:
            insert_response = (
                supabase.table("projects")
                .insert(payload)
                .execute()
            )

            if insert_response.data:
                existing_projects.append(payload)
                results["inserted"] += 1
            else:
                results["failed"] += 1
                record_failure(
                    project,
                    "Supabase insert returned no inserted record.",
                )

        except Exception as exc:
            error_msg = str(exc)

            if (
                "duplicate key value violates unique constraint" in error_msg
                or "23505" in error_msg
            ):
                results["duplicate_skipped"] += 1
            else:
                logger.warning(
                    "Failed to insert project '%s': %s",
                    getattr(project, "title", ""),
                    exc,
                )
                results["failed"] += 1
                record_failure(
                    project,
                    f"{type(exc).__name__}: {error_msg}",
                )

    return results

@app.post(
    "/scrape/truelancer/manual",
    response_model=ManualTruelancerFetchResponse,
)
def trigger_manual_truelancer_fetch(
    request_body: Optional[ManualTruelancerFetchRequest] = None,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """
    Trigger a manual Truelancer scraping run using the existing pipeline and provider config.
    Accessible to any authenticated user.
    """
    try:
        sources_response = supabase.table("sources").select("*").execute()
    except Exception:
        logger.exception("Failed to query sources for manual Truelancer fetch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load source configuration from the database.",
        )

    truelancer_sources = [
        s for s in (sources_response.data or [])
        if isinstance(s, dict) and (s.get("name") or "").strip().casefold() == "truelancer"
    ]

    if not truelancer_sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Truelancer source is not configured in the database.",
        )

    active_source = next(
        (s for s in truelancer_sources if s.get("is_active") is not False),
        None,
    )
    if active_source is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Truelancer source is currently inactive. Activate it before fetching.",
        )

    source_id = str(active_source["id"])
    source_name = active_source.get("name") or "Truelancer"
    start_url = _resolve_truelancer_start_url(active_source)

    max_pages = (
        request_body.max_pages
        if request_body and request_body.max_pages is not None
        else int(os.getenv("SCHEDULER_MAX_PAGES", "3"))
    )
    min_request_interval = (
        request_body.min_request_interval
        if request_body and request_body.min_request_interval is not None
        else float(os.getenv("SCHEDULER_MIN_REQUEST_INTERVAL", "1.0"))
    )
    resolved_provider = (
        request_body.provider
        if request_body and request_body.provider is not None
        else os.getenv("SCRAPING_PROVIDER", "direct").strip().lower()
    )

    try:
        pipeline_result = run_truelancer_pipeline(
            source_id=source_id,
            start_url=start_url,
            max_pages=max_pages,
            min_request_interval=min_request_interval,
            provider=resolved_provider,
            run_creator=_backend_create_scraping_run,
            run_updater=_backend_update_scraping_run,
            submitter=lambda projs: _backend_submit_projects(projs, source_id),
        )
    except ScraperAPIConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=redact_api_key(str(exc)),
        )
    except (ScraperAPIAccessError, ScrapingAccessError, ScraperAPIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=redact_api_key(str(exc)),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=redact_api_key(str(exc)),
        )
    except Exception as exc:
        logger.exception("Manual Truelancer fetch failed unexpectedly")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=redact_api_key(
                f"Manual Truelancer fetch failed: {type(exc).__name__}"
            ),
        )

    submission = pipeline_result.get("submission") or {}
    return ManualTruelancerFetchResponse(
        run_id=str(pipeline_result["run_id"]),
        source_id=source_id,
        source_name=source_name,
        provider=resolved_provider,
        start_url=start_url,
        status=str(pipeline_result["status"]),
        records_found=int(pipeline_result.get("records_found", 0)),
        inserted=int(submission.get("inserted", 0)),
        duplicate_skipped=int(submission.get("duplicate_skipped", 0)),
        irrelevant_skipped=int(submission.get("irrelevant_skipped", 0)),
        missing_url_skipped=int(submission.get("missing_url_skipped", 0)),
        invalid_skipped=int(submission.get("invalid_skipped", 0)),
        failed=int(submission.get("failed", 0)),
        submission=submission,
    )


# ============================================================
# RECURRING SCHEDULER ENDPOINTS
# ============================================================

def _is_missing_schedules_table_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "scraping_schedules" in msg and (
        "does not exist" in msg
        or "could not find the table" in msg
        or "pgrst205" in msg
        or "42p01" in msg
    )


def _execute_persisted_schedule(schedule_id: str):
    """Execute one persisted recurring schedule against the Truelancer pipeline."""
    now_utc = datetime.now(timezone.utc)
    try:
        sched_resp = (
            supabase.table("scraping_schedules")
            .select("*")
            .eq("id", str(schedule_id))
            .execute()
        )
        if not sched_resp.data:
            logger.warning("Scheduled job %s skipped: schedule not found.", schedule_id)
            return None
        schedule = sched_resp.data[0]
        if not schedule.get("is_enabled", True):
            logger.info("Scheduled job %s skipped: schedule is paused.", schedule_id)
            return None

        source_id = str(schedule["source_id"])
        src_resp = (
            supabase.table("sources")
            .select("*")
            .eq("id", source_id)
            .execute()
        )
        if not src_resp.data:
            raise ValueError("Configured source was not found.")
        source = src_resp.data[0]
        if source.get("is_active") is False:
            raise ValueError("Configured source is inactive.")

        (
            supabase.table("scraping_schedules")
            .update({
                "last_run_at": now_utc.isoformat(),
                "last_run_status": "RUNNING",
                "last_error": None,
                "updated_at": now_utc.isoformat(),
            })
            .eq("id", str(schedule_id))
            .execute()
        )

        start_url = _resolve_truelancer_start_url(source)
        provider = os.getenv("SCRAPING_PROVIDER", "direct").strip().lower()
        result = run_truelancer_pipeline(
            source_id=source_id,
            start_url=start_url,
            max_pages=int(schedule.get("max_pages") or 3),
            min_request_interval=float(schedule.get("min_request_interval") or 1.0),
            provider=provider,
            run_creator=_backend_create_scraping_run,
            run_updater=_backend_update_scraping_run,
            submitter=lambda projs: _backend_submit_projects(projs, source_id),
        )

        next_dt = calculate_next_run_time(schedule)
        final_status = str(result.get("status") or "SUCCESS")
        (
            supabase.table("scraping_schedules")
            .update({
                "last_run_status": final_status,
                "last_error": None if final_status == "SUCCESS" else "One or more submissions failed.",
                "next_run_at": next_dt.isoformat() if next_dt else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(schedule_id))
            .execute()
        )
        return result
    except Exception as exc:
        logger.exception("Persisted schedule %s execution failed", schedule_id)
        try:
            next_dt = None
            sched_resp = (
                supabase.table("scraping_schedules")
                .select("*")
                .eq("id", str(schedule_id))
                .execute()
            )
            if sched_resp.data:
                next_dt = calculate_next_run_time(sched_resp.data[0])
            (
                supabase.table("scraping_schedules")
                .update({
                    "last_run_at": now_utc.isoformat(),
                    "last_run_status": "FAILED",
                    "last_error": redact_api_key(str(exc))[:1000],
                    "next_run_at": next_dt.isoformat() if next_dt else None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", str(schedule_id))
                .execute()
            )
        except Exception:
            logger.exception("Failed to record error status for schedule %s", schedule_id)
        return None


def _sync_persisted_schedules():
    """Load persisted schedules from Supabase and sync with APScheduler."""
    response = supabase.table("scraping_schedules").select("*").execute()
    schedules = response.data or []
    return sync_schedules_to_scheduler(schedules, _execute_persisted_schedule)


def _enrich_schedule_row(row: dict) -> dict:
    """Ensure next_run_at reflects the real calculated next execution time."""
    enriched = dict(row)
    if enriched.get("is_enabled", True):
        try:
            next_dt = calculate_next_run_time(enriched)
            enriched["next_run_at"] = next_dt.isoformat() if next_dt else None
        except Exception:
            pass
    else:
        enriched["next_run_at"] = None
    return enriched


@app.get("/schedules/status")
def get_scheduler_status(current_user: CurrentUser = Depends(require_authenticated)):
    """Return whether background scheduled execution is enabled and running."""
    sched = get_scheduler()
    return {
        "scheduler_enabled": is_scheduler_enabled_in_env(),
        "running": bool(sched is not None and sched.running),
        "default_timezone": "Asia/Kolkata",
    }


@app.get(
    "/schedules",
    response_model=List[ScheduleResponse],
)
def list_schedules(current_user: CurrentUser = Depends(require_authenticated)):
    """List all saved recurring scraping schedules."""
    try:
        response = (
            supabase.table("scraping_schedules")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [_enrich_schedule_row(row) for row in (response.data or [])]
    except Exception as exc:
        if _is_missing_schedules_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Schedules table is not initialized. Apply migrations/05_scraping_schedules.sql.",
            )
        logger.exception("Failed to list schedules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch schedules due to a server error.",
        )


@app.post(
    "/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    payload: ScheduleCreate,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """Create a persistent recurring scraping schedule for an active source."""
    try:
        src_resp = (
            supabase.table("sources")
            .select("*")
            .eq("id", str(payload.source_id))
            .execute()
        )
        if not src_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected source was not found.",
            )
        if src_resp.data[0].get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create a schedule for an inactive source.",
            )

        schedule_data = payload.model_dump(mode="json")
        try:
            build_trigger_for_schedule(schedule_data)
            next_dt = calculate_next_run_time(schedule_data)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        schedule_data["next_run_at"] = next_dt.isoformat() if next_dt else None
        schedule_data["created_by"] = current_user.id

        insert_resp = (
            supabase.table("scraping_schedules")
            .insert(schedule_data)
            .execute()
        )
        if not insert_resp.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Schedule creation returned no data.",
            )

        try:
            _sync_persisted_schedules()
        except Exception as sync_exc:
            logger.warning("Schedule saved but APScheduler sync skipped: %s", sync_exc)

        return _enrich_schedule_row(insert_resp.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        if _is_missing_schedules_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Schedules table is not initialized. Apply migrations/05_scraping_schedules.sql.",
            )
        logger.exception("Failed to create schedule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create schedule due to a server error.",
        )


@app.patch(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
def update_schedule(
    schedule_id: UUID,
    payload: ScheduleUpdate,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """Update an existing recurring scraping schedule."""
    update_data = payload.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one schedule field must be provided.",
        )

    try:
        existing_resp = (
            supabase.table("scraping_schedules")
            .select("*")
            .eq("id", str(schedule_id))
            .execute()
        )
        if not existing_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule was not found.",
            )

        merged = {**existing_resp.data[0], **update_data}
        if "source_id" in update_data:
            src_resp = (
                supabase.table("sources")
                .select("*")
                .eq("id", str(update_data["source_id"]))
                .execute()
            )
            if not src_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected source was not found.",
                )
            if src_resp.data[0].get("is_active") is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign schedule to an inactive source.",
                )

        try:
            build_trigger_for_schedule(merged)
            next_dt = calculate_next_run_time(merged)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        update_data["next_run_at"] = next_dt.isoformat() if next_dt else None
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        update_resp = (
            supabase.table("scraping_schedules")
            .update(update_data)
            .eq("id", str(schedule_id))
            .execute()
        )
        if not update_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule was not found.",
            )

        try:
            _sync_persisted_schedules()
        except Exception as sync_exc:
            logger.warning("Schedule updated but APScheduler sync skipped: %s", sync_exc)

        return _enrich_schedule_row(update_resp.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        if _is_missing_schedules_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Schedules table is not initialized. Apply migrations/05_scraping_schedules.sql.",
            )
        logger.exception("Failed to update schedule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update schedule due to a server error.",
        )


@app.post(
    "/schedules/{schedule_id}/pause",
    response_model=ScheduleResponse,
)
def pause_schedule(
    schedule_id: UUID,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """Pause a recurring schedule."""
    return update_schedule(
        schedule_id=schedule_id,
        payload=ScheduleUpdate(is_enabled=False),
        current_user=current_user,
    )


@app.post(
    "/schedules/{schedule_id}/resume",
    response_model=ScheduleResponse,
)
def resume_schedule(
    schedule_id: UUID,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """Resume a paused recurring schedule."""
    return update_schedule(
        schedule_id=schedule_id,
        payload=ScheduleUpdate(is_enabled=True),
        current_user=current_user,
    )


@app.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_schedule(
    schedule_id: UUID,
    current_user: CurrentUser = Depends(require_authenticated),
):
    """Delete a recurring schedule."""
    try:
        (
            supabase.table("scraping_schedules")
            .delete()
            .eq("id", str(schedule_id))
            .execute()
        )
        try:
            _sync_persisted_schedules()
        except Exception as sync_exc:
            logger.warning("Schedule deleted but APScheduler sync skipped: %s", sync_exc)
        return None
    except Exception as exc:
        if _is_missing_schedules_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Schedules table is not initialized. Apply migrations/05_scraping_schedules.sql.",
            )
        logger.exception("Failed to delete schedule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete schedule due to a server error.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
