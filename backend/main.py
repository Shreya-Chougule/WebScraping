
import os
from typing import List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

from schemas import (
    ProjectCreate, ProjectResponse,
    SourceCreate, SourceResponse,
    KeywordCreate, KeywordResponse
)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase environment variables are missing.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Project Discovery Tool API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Project Discovery Tool Backend is Running!"}


@app.get("/test-db")
def test_db_connection():
    try:
        response = supabase.table("projects").select("*").limit(5).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- PROJECT ENDPOINTS ---

@app.get("/projects", response_model=List[ProjectResponse])
def get_projects():
    try:
        response = supabase.table("projects").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching projects: {str(e)}"
        )


@app.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED
)
def create_project(project: ProjectCreate):
    try:
        project_data = project.model_dump(
            mode="json",
            exclude_none=True
        )

        response = supabase.table("projects").insert(project_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Project insertion returned no data."
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as e:
        error_msg = str(e)

        if (
            "duplicate key value violates unique constraint" in error_msg
            or "23505" in error_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with this unique value already exists."
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inserting project: {error_msg}"
        )


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str):
    try:
        supabase.table("projects").delete().eq("id", project_id).execute()
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )


# --- SOURCE ENDPOINTS ---

@app.get("/sources", response_model=List[SourceResponse])
def get_sources():
    try:
        response = supabase.table("sources").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED
)
def create_source(source: SourceCreate):
    try:
        source_data = source.model_dump(
            mode="json",
            exclude_none=True
        )

        response = supabase.table("sources").insert(source_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Source insertion returned no data."
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
