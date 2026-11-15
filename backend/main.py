
import os
import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta, date, time
from typing import List, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from supabase import create_client, Client


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
    from backend.route_security import ProductionAuthMiddleware
except ImportError:
    from route_security import ProductionAuthMiddleware
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Project Discovery Tool API")


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

        project_types = ["Web", "App", "Software", "Both"]
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
            .select("id,name")
            .execute()
        )

        projects_by_source = []

        for source in sources_response.data or []:
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

        return {
            "total_projects": total_projects,
            "projects_today": projects_today,
            "projects_by_type": projects_by_type,
            "projects_by_source": projects_by_source,
            "scraping_runs": scraping_runs,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )
