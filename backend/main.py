import os
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from schemas import (
    ProjectCreate,
    ProjectResponse,
    SourceCreate,
    SourceResponse,
    KeywordCreate,
    KeywordResponse,
    ScrapingRunCreate,
    ScrapingRunUpdate,
    ScrapingRunResponse,
)


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Project Discovery Tool API")


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    try:
        response = (
            supabase.table("projects")
            .select("*")
            .limit(5)
            .execute()
        )

        return {
            "status": "success",
            "data": response.data,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


# ============================================================
# PROJECT ENDPOINTS
# ============================================================

@app.get(
    "/projects",
    response_model=List[ProjectResponse],
)
def get_projects():
    try:
        response = (
            supabase.table("projects")
            .select("*")
            .execute()
        )

        return response.data

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching projects: {str(exc)}",
        )


@app.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(project: ProjectCreate):
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

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
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
            detail=f"Error inserting project: {error_msg}",
        )


@app.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(project_id: str):
    try:
        (
            supabase.table("projects")
            .delete()
            .eq("id", project_id)
            .execute()
        )

        return None

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(exc)}",
        )


# ============================================================
# SOURCE ENDPOINTS
# ============================================================

@app.get(
    "/sources",
    response_model=List[SourceResponse],
)
def get_sources():
    try:
        response = (
            supabase.table("sources")
            .select("*")
            .execute()
        )

        return response.data

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.post(
    "/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source(source: SourceCreate):
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ============================================================
# SCRAPING RUN ENDPOINTS
# ============================================================

@app.post(
    "/scraping-runs",
    response_model=ScrapingRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scraping_run_endpoint(
    scraping_run: ScrapingRunCreate,
):
    """
    Create a scraping-run record with RUNNING status.
    """
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

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating scraping run: {str(exc)}",
        )


@app.patch(
    "/scraping-runs/{run_id}",
    response_model=ScrapingRunResponse,
)
def update_scraping_run_endpoint(
    run_id: str,
    scraping_run: ScrapingRunUpdate,
):
    """
    Complete a scraping run with SUCCESS or FAILED status.
    """
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
            .eq("id", run_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scraping run was not found.",
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating scraping run: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )