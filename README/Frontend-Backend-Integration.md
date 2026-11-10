# ScrapeScout – Frontend and Backend Integration Documentation

**Project:** ScrapeScout – EDI Web & App Project Discovery Tool  
**Date:** November 10, 2026  
**Integration Commit:** `d591ce4`  
**Backend:** Python – FastAPI  
**Frontend:** React.js  
**Database:** Supabase (PostgreSQL)

---

## 1. Introduction

This document describes the integration of the ScrapeScout frontend application with its FastAPI backend.

The integration connects the React-based dashboard to backend REST APIs so that project information, dashboard analytics, search results, daily opportunities, and CSV exports can be retrieved from the backend.

Previously, several frontend operations relied on locally managed data. After integration, the frontend communicates with the backend APIs to retrieve and manage project information.

## 2. System Architecture

The integrated application follows a three-layer architecture:

1. **Frontend Layer:** React.js application responsible for the user interface and user interactions.
2. **Backend Layer:** FastAPI application responsible for API requests, filtering, processing, validation, and business logic.
3. **Database Layer:** Supabase PostgreSQL database responsible for persistent project and application data.

### Application Data Flow

```text
User
  |
  v
React Frontend
  |
  | HTTP Requests (REST API)
  v
FastAPI Backend
  |
  | Database Operations
  v
Supabase PostgreSQL
  |
  v
FastAPI JSON / CSV Response
  |
  v
React Frontend
  |
  v
Dashboard / Search / Daily Opportunities / Export
```

## 3. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js |
| Frontend Styling | CSS |
| Backend | Python |
| API Framework | FastAPI |
| API Server | Uvicorn |
| Database | Supabase PostgreSQL |
| API Communication | HTTP / REST |
| Data Format | JSON |
| Export Format | CSV |
| Cross-Origin Support | FastAPI CORSMiddleware |

## 4. Backend API Configuration

The backend application is located in:

`backend/main.py`

The FastAPI application is initialized using:

```python
app = FastAPI(title="Project Discovery Tool API")
```

### CORS Configuration

Cross-Origin Resource Sharing (CORS) is enabled to allow the React frontend and FastAPI backend to communicate when running on different local development ports.

Current configuration:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production consideration:** The wildcard origin should be replaced with explicitly permitted frontend origins before production deployment. Credentials should only be enabled when the authentication design requires them.

### Supabase Connection

The backend loads its database credentials through environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

The service-role key must remain on the backend and must never be exposed in frontend code.

## 5. Frontend API Configuration

The main frontend application is located in:

`frontend/src/App.js`

The API base URL is configured as:

```javascript
const API_BASE_URL = (
  process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');
```

This allows the frontend to communicate with the locally running FastAPI backend.

For another environment, the frontend API URL can be configured using:

`REACT_APP_API_BASE_URL`

Example:

```env
REACT_APP_API_BASE_URL=http://127.0.0.1:8000
```

The frontend uses HTTP requests to retrieve data and submit operations to the backend.

## 6. Integrated API Endpoints

The following backend endpoints are connected to the frontend.

| API Endpoint | Method | Frontend Functionality |
|---|---|---|
| `/analytics/dashboard` | GET | Retrieves dashboard analytics |
| `/projects` | GET | Retrieves project records |
| `/projects/search` | GET | Retrieves filtered and searched projects |
| `/projects` | POST | Adds a new opportunity |
| `/projects/{project_id}` | DELETE | Deletes a project |
| `/analytics/daily-opportunities` | GET | Retrieves daily or historical opportunities |
| `/projects/export` | GET | Exports filtered project records as CSV |
| `/` | GET | Backend root endpoint |

## 7. Integrated Frontend Modules

### 7.1 Dashboard Analytics

The dashboard retrieves its statistics from:

`GET /analytics/dashboard`

The response provides:

- Total projects.
- Projects added today.
- Project counts by type.
- Project counts by source.
- Scraping run statistics.

The frontend uses these values to populate the dashboard cards and summary sections.

### 7.2 Project Listing

The frontend retrieves project information from the backend.

The project listing displays available opportunity information and supports loading additional results through pagination.

### 7.3 Search and Filtering

The search module communicates with:

`GET /projects/search`

Supported backend query parameters include:

- `search`
- `project_type`
- `technology`
- `location`
- `source_id`
- `category`
- `posted_from`
- `posted_to`
- `limit`
- `offset`

The frontend sends the search and filter values currently supported by its user interface, including keyword search, project type, and category.

The backend performs the filtering and returns the matching project records.

### 7.4 Daily Project Opportunities

The daily opportunities section communicates with:

`GET /analytics/daily-opportunities`

It supports date-based retrieval of project opportunities.

The frontend provides a date selector and displays the corresponding response, including:

- Selected date.
- Total number of opportunities.
- Project details.
- Historical-date information.

The backend uses the `Asia/Kolkata` timezone to calculate the daily date boundaries.

### 7.5 Add Opportunity

The frontend submits new project information using:

`POST /projects`

The backend validates the submitted information and handles database insertion and duplicate conflicts.

### 7.6 Delete Opportunity

The frontend sends a DELETE request to:

`DELETE /projects/{project_id}`

The backend processes the deletion request and returns the corresponding API response.

### 7.7 CSV Export

The export functionality communicates with:

`GET /projects/export`

The frontend sends the active search and filter parameters to the backend.

The backend generates a CSV response containing matching project records. The frontend receives the response as a Blob and initiates a browser download.

This makes export consistent with the backend search and filtering logic.

### 7.8 Scraping Run Statistics

The dashboard displays scraping run statistics retrieved through the dashboard analytics endpoint.

The displayed information includes:

- Total scraping runs.
- Successful runs.
- Failed runs.
- Currently running jobs.

## 8. Running the Integrated Application

Both the frontend and backend must be running simultaneously during local development.

### Step 1: Activate the Python Virtual Environment

From the project root directory, open PowerShell and run:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 2: Start the Backend

Run:

```powershell
uvicorn backend.main:app --reload
```

Backend URL:

`http://127.0.0.1:8000`

FastAPI interactive API documentation:

`http://127.0.0.1:8000/docs`

### Step 3: Start the Frontend

Open a second terminal in the project root directory.

Run:

```powershell
npm --prefix .\frontend start
```

Frontend URL:

`http://localhost:3000`

### Step 4: Use the Application

Open the frontend in a browser.

The frontend sends requests to the backend, which retrieves or processes the required information and returns the API responses.

**Important:** Keep both terminal processes running while using the integrated application.

## 9. Error Handling

The frontend handles API request failures and displays error messages when requests cannot be completed.

Common integration issues include:

| Error | Possible Cause |
|---|---|
| NetworkError | Backend is not running or cannot be reached |
| CORS error | Frontend origin is not permitted by backend CORS settings |
| HTTP 404 | Requested API endpoint does not exist |
| HTTP 422 | Invalid request parameters or request data |
| HTTP 500 | Backend processing or database error |

If the backend cannot start, check its terminal output before troubleshooting the frontend.

## 10. Security Considerations

The following security improvements should be addressed before production deployment:

1. Restrict CORS to approved frontend origins.
2. Implement actual user authentication.
3. Protect sensitive API endpoints.
4. Implement role-based access control.
5. Keep Supabase service-role credentials exclusively on the backend.
6. Validate and sanitize user-submitted data.
7. Review CSV export handling to prevent spreadsheet formula injection.
8. Configure HTTPS for production deployment.

The current frontend login interface is client-side only and does not provide actual backend authentication or authorization.

## 11. Current Integration Status

The frontend and backend integration has been implemented.

| Feature | Status |
|---|---|
| React frontend and FastAPI communication | Integrated |
| Dashboard analytics | Integrated |
| Project listing | Integrated |
| Search and filtering | Integrated |
| Daily opportunities | Integrated |
| Add opportunity | Integrated |
| Delete opportunity | Integrated |
| Backend CSV export | Integrated |
| Scraping run statistics | Integrated |
| Local frontend and backend startup | Working |

The application successfully starts locally, and the dashboard loads its backend data.

Individual write and export operations should also be exercised as part of the subsequent end-to-end testing process.

## 12. Future Improvements

The following improvements are planned or remain relevant:

- Implement actual authentication and authorization.
- Add protected frontend routes.
- Implement role-based access control.
- Complete automated scheduler lifecycle integration.
- Improve scraping retry and recovery handling.
- Perform end-to-end testing of the scraping-to-database-to-dashboard workflow.
- Configure production deployment and monitoring.
- Apply production security configurations.

## 13. Git Integration Commit

The frontend–backend integration changes were committed under:

**Commit:** `d591ce4`

**Commit Message:**

`Integrate ScrapeScout frontend with backend APIs`

The commit contains changes to:

- `backend/main.py`
- `frontend/src/App.js`
- `frontend/src/App.css`

---

**Conclusion**

The ScrapeScout frontend and backend have been connected through REST API communication. The React dashboard now retrieves analytics and project information from the FastAPI backend, supports backend-powered search and filtering, displays daily opportunities, and uses backend CSV export functionality.

This integration establishes the application communication layer required for further development, testing, security improvements, and deployment.