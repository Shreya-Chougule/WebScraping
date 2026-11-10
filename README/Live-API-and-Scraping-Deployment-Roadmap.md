# ScrapeScout – Live API Server & Scraping Deployment Roadmap

**Document Date:** 10 November 2026  
**Project:** ScrapeScout – EDI Web & App Project Discovery Tool  
**Scope:** Live Backend API, Truelancer Scraping, Database Connectivity and Frontend Integration  
**Deployment Platform (Planned):** Render  
**Database:** Supabase PostgreSQL

---

## 1. Project Overview

ScrapeScout is a web-based project discovery system designed to collect genuine freelance opportunities related to website development, web applications, mobile applications and software development.

The purpose of this roadmap is to take the existing locally working ScrapeScout application and prepare it for live operation.

The deployment workflow will connect the existing Python scraping system, FastAPI backend, Supabase database and React frontend.

The focus is to make the complete application accessible through a publicly hosted API and enable reliable automated scraping.

## 2. Current Implementation Status

The following components have already been implemented locally:

| Component | Current Status |
|---|---|
| Truelancer scraper implementation | Implemented |
| Data extraction and parsing | Implemented |
| Keyword-based classification | Implemented |
| Project validation | Implemented |
| Duplicate detection | Implemented |
| Automated pipeline | Partially implemented |
| APScheduler integration | Implemented, lifecycle integration pending |
| FastAPI backend APIs | Implemented |
| Supabase database integration | Implemented locally |
| Dashboard frontend | Implemented |
| Search and filtering | Implemented |
| Daily opportunities | Implemented |
| CSV export | Implemented |
| Frontend-backend integration | Completed locally |
| Live API hosting | Pending |
| Live scraping execution | Pending |
| Production scheduler | Pending |

**Important:** Existing working functionality should be preserved. New implementation should focus on deployment readiness and live execution rather than unnecessarily rebuilding existing modules.

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Hosting | Render |
| Scraping | Requests and BeautifulSoup / existing scraper implementation |
| Classification | Existing Python keyword-based classifier |
| Deduplication | Existing Python deduplication module |
| Scheduling | APScheduler |
| API communication | REST APIs |
| Version control | Git and GitHub |

No additional AI classification API, including Groq, will be introduced. The existing keyword-based classification system will remain the single classification mechanism.

## 4. Deployment Roadmap

### Phase 1 – Backend Production Preparation

**Objective:** Prepare the existing FastAPI backend for deployment.

Tasks:
- Inspect the existing backend startup configuration.
- Review and organize Python dependencies.
- Confirm the production application entry point.
- Configure environment-variable-based settings.
- Ensure Supabase credentials are not hardcoded.
- Review CORS configuration for the deployed frontend.
- Prepare the appropriate production start command.
- Ensure startup does not unintentionally trigger live scraping.

**Expected Deliverable:** Backend ready for hosting.

**Completion Criteria:**
- Backend starts using the production command.
- Required dependencies are available.
- Environment variables are configured securely.
- Existing API functionality is preserved.

### Phase 2 – FastAPI Hosting on Render

**Objective:** Host the backend on a publicly accessible server.

Tasks:
- Create and configure a Render web service.
- Connect the existing GitHub repository.
- Configure the build command.
- Configure the production start command.
- Add required environment variables.
- Deploy the backend.
- Obtain the public API URL.
- Confirm the API health endpoint responds successfully.

**Expected Deliverable:** Publicly accessible FastAPI backend.

**Completion Criteria:**
- Deployment succeeds.
- Public API URL is available.
- API health endpoint responds.
- Application logs are accessible.

### Phase 3 – Production Supabase Connectivity

**Objective:** Connect the hosted backend securely to Supabase.

Tasks:
- Configure the Supabase project URL.
- Configure the required server-side database credentials.
- Store credentials in Render environment variables.
- Verify database connectivity.
- Confirm existing table access.
- Check project insertion and retrieval operations.
- Confirm scraping-run records can be managed.

**Expected Deliverable:** Hosted backend connected to Supabase.

**Completion Criteria:**
- Backend can access the database.
- Existing records can be retrieved.
- Authorized database operations work correctly.
- Credentials are not exposed in frontend code or GitHub.

### Phase 4 – Live Truelancer Scraping

**Objective:** Execute the existing scraper against the selected source under the applicable website access rules.

Tasks:
- Review the existing Truelancer scraper configuration.
- Confirm the source is enabled and configured correctly.
- Execute a controlled live scraping run.
- Extract available project information.
- Clean and standardize extracted values.
- Apply existing keyword-based classification.
- Validate extracted records.
- Run duplicate detection.
- Submit eligible records through the existing backend pipeline.
- Confirm successfully inserted records in Supabase.

**Expected Deliverable:** Live Truelancer opportunities stored in Supabase.

**Completion Criteria:**
- Live scraping executes successfully.
- Extracted records contain the available required fields.
- Invalid records are handled appropriately.
- Duplicate records are not inserted again.
- Successful records are accessible through the backend APIs.

### Phase 5 – Automated Scraping Scheduler

**Objective:** Enable reliable automated execution of the scraping pipeline.

Tasks:
- Connect APScheduler to FastAPI startup and shutdown lifecycle.
- Configure the scraping interval.
- Prevent overlapping scraping jobs.
- Handle unexpected job failures.
- Implement suitable retry and recovery handling.
- Record execution status and errors.
- Ensure server restarts do not create duplicate scheduled jobs.
- Confirm scheduler behavior in the hosted environment.

**Expected Deliverable:** Automated scraping pipeline running on the hosted server.

**Completion Criteria:**
- Scheduler starts and stops correctly.
- Scraping executes at the configured interval.
- Failed runs are recorded.
- Overlapping executions are prevented.
- Failures do not crash the entire backend.

### Phase 6 – Frontend Connection to Live API

**Objective:** Connect the existing React application to the hosted FastAPI backend.

Tasks:
- Configure the production API base URL.
- Use environment variables for frontend API configuration.
- Rebuild the React application.
- Verify dashboard analytics.
- Verify search and filtering.
- Verify daily opportunities.
- Verify project creation and deletion where enabled.
- Verify CSV export.
- Verify error handling and loading states.

**Expected Deliverable:** React frontend communicating with the publicly hosted backend.

**Completion Criteria:**
- Frontend loads successfully.
- API requests use the deployed backend URL.
- Existing dashboard functionality works.
- Search and filters return backend data.
- Daily opportunities load correctly.
- CSV export works through the hosted API.

### Phase 7 – Complete Live Workflow Testing

**Objective:** Confirm that the entire application works as one integrated system.

Complete workflow:

Truelancer → Scraper → Data Extraction → Classification → Validation → Deduplication → FastAPI → Supabase → React Frontend.

Tasks:
- Execute an end-to-end live workflow.
- Confirm extracted opportunities reach the database.
- Confirm records appear on the dashboard.
- Confirm search and filters work with live records.
- Confirm daily opportunities display correctly.
- Confirm CSV export contains the expected records.
- Check scraping-run status and error handling.
- Resolve any issues discovered during execution.

**Expected Deliverable:** Fully connected live ScrapeScout application.

**Completion Criteria:**
- End-to-end data flow works.
- Database and frontend show consistent data.
- No critical integration issues remain.

## 5. Security and Reliability Considerations

The following requirements must be considered throughout implementation:

1. Never commit Supabase service-role keys or other secrets to GitHub.
2. Keep backend credentials on the server.
3. Configure CORS for the actual frontend origin in production.
4. Respect Truelancer's applicable terms, access restrictions and robots directives.
5. Avoid bypassing authentication, CAPTCHAs or other access controls.
6. Handle HTTP errors, timeouts and temporary source downtime.
7. Avoid inserting duplicate records.
8. Prevent overlapping scheduled executions.
9. Maintain useful application and scraping logs.
10. Avoid exposing sensitive internal errors through public API responses.

## 6. Work Division

### Our responsibility – Live API and Scraping

- Backend production preparation.
- Render API hosting.
- Supabase production connectivity.
- Live Truelancer scraping.
- Production scraping pipeline.
- Scheduler deployment.
- Connecting frontend to the live API.
- End-to-end live workflow.

### Teammate responsibility – Phases 14–17

- Phase 14: Authentication and access control.
- Phase 15: Notifications.
- Phase 16: Quality assurance and testing.
- Phase 17: Security and performance improvements.

These tasks must remain compatible with the existing implementation and the live API work.

### Joint responsibility – Final project completion

- Phase 18: Final deployment.
- Phase 19: Monitoring and maintenance.

These final project-wide phases will be handled after the remaining implementation work is completed.

## 7. Risks and Limitations

| Risk | Planned Handling |
|---|---|
| Hosting service restarts | Configure reliable startup and scheduler lifecycle |
| Database connection failure | Handle connection errors and log failures |
| Truelancer access restrictions | Respect website policies and handle blocked requests |
| Duplicate opportunities | Use existing deduplication logic |
| Scraping failures | Record failed runs and implement recovery handling |
| Missing project information | Preserve available fields and handle missing values |
| API downtime | Monitor service health and application logs |
| Frontend API connection errors | Configure the correct production API URL and CORS |

## 8. Progress Tracker

The following tracker will be updated as implementation progresses.

| Phase | Task | Status |
|---|---|---|
| 1 | Backend production preparation | Not Started |
| 2 | Render API hosting | Not Started |
| 3 | Production Supabase connectivity | Not Started |
| 4 | Live Truelancer scraping | Not Started |
| 5 | Automated scheduler deployment | Not Started |
| 6 | Frontend live API connection | Not Started |
| 7 | Complete live workflow testing | Not Started |

## 9. Final Deployment Checklist

- [ ] Backend production configuration completed.
- [ ] Render service deployed.
- [ ] Public API URL obtained.
- [ ] Supabase production connectivity confirmed.
- [ ] Live Truelancer scraping completed.
- [ ] Classification and deduplication working.
- [ ] Valid records stored in Supabase.
- [ ] APScheduler running correctly.
- [ ] React frontend connected to live API.
- [ ] Dashboard displays live data.
- [ ] Search and filtering work.
- [ ] Daily opportunities work.
- [ ] CSV export works.
- [ ] End-to-end workflow completed.
- [ ] Remaining team implementation phases completed.
- [ ] Final deployment and monitoring phases completed.

## 10. Implementation Approach

Implementation will follow a sequential approach.

- Complete one phase before moving to the next dependent phase.
- Preserve existing working code wherever possible.
- Make changes in the appropriate existing project files.
- Use controlled testing before enabling live automated execution.
- Update this document after completing each phase.
- Record important configuration decisions and deployment details.
- Keep all credentials and secrets outside version control.

**Immediate Next Step:** Begin Phase 1 – Backend Production Preparation.

**Final Goal:** Make ScrapeScout a publicly accessible, database-connected and automatically operating freelance opportunity discovery application.