import os
from typing import List, Optional
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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Project Discovery Tool API")

# Configure CORS for Frontend integration
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
        response = supabase.table("projects").select("*").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- PROJECTS ENDPOINTS ---

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

@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate):
    try:
        project_data = project.model_dump(mode="json", exclude_none=True)
        response = supabase.table("projects").insert(project_data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create project.")
        return response.data[0]
    except Exception as e:
        error_msg = str(e)
        if "duplicate key value violates unique constraint" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project with this original_url already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inserting project: {error_msg}"
        )

# --- SOURCES ENDPOINTS ---

@app.get("/sources", response_model=List[SourceResponse])
def get_sources():
    try:
        response = supabase.table("sources").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(source: SourceCreate):
    try:
        source_data = source.model_dump(mode="json", exclude_none=True)
        response = supabase.table("sources").insert(source_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # --- DELETE PROJECT ENDPOINT ---

@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str):
    try:
        response = supabase.table("projects").delete().eq("id", project_id).execute()
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )