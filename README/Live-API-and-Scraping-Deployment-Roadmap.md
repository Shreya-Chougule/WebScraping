# ScrapeScout – Live API and Scraping Deployment Roadmap

## 1. Document Purpose

This document defines the implementation and verification roadmap for connecting the live scraping system with the backend API, Supabase database, and frontend application.

The objective is to move from locally tested scraping functionality to a verified workflow that can retrieve freelance project listings, process them, store them, and display them through the application.

This document focuses on the live data-collection and deployment workflow rather than repeating the complete project development roadmap.

---

## 2. Current System Architecture

The intended live workflow is:

**Truelancer → ScraperAPI → Scraping and Extraction Pipeline → Data Validation → Classification → Duplicate Detection → FastAPI → Supabase → Frontend Dashboard**

### 2.1 Components

**Source Platform**

Truelancer is the initial live source for collecting freelance project opportunities.

**Fetching Provider**

ScraperAPI is integrated as a configurable website-fetching provider.

**Scraping and Extraction**

The scraper retrieves the source response, extracts project information, and follows pagination where supported.

**Data Processing**

The extracted records pass through cleaning, validation, classification, and duplicate detection.

**Backend API**

FastAPI receives valid processed records and provides endpoints for application operations.

**Database**

Supabase PostgreSQL stores the collected project records and related scraping information.

**Frontend**

The React dashboard displays project information retrieved through the backend APIs.

---

## 3. Live Fetching Provider Configuration

**Status: Integrated; Live Production Verification Pending**

### Objective

Use ScraperAPI as the configured fetching provider for website retrieval.

### Implementation

- ScraperAPI provider module is integrated.
- Fetching logic is reusable across supported scraping workflows.
- Provider selection is controlled through environment configuration.
- The scraper and pipeline use the configured provider.
- API credentials are stored in environment variables.
- The API key must not be hardcoded or committed to the repository.

### Configuration

The environment configuration includes:

`SCRAPING_PROVIDER=scraperapi`

The actual ScraperAPI credential must remain in the local environment or the deployment platform's secret configuration.

### Verification Activities

- Verify that the provider configuration is loaded correctly.
- Verify that the scraper selects ScraperAPI.
- Verify that API credentials are available to the application without exposing them.
- Verify successful responses through controlled requests.
- Verify timeout and error handling.
- Verify that unsuccessful responses do not produce invalid project records.

### Expected Outcome

A reusable and configurable fetching layer that can be used by the Truelancer scraping pipeline.

---

## 4. Truelancer Live Extraction

**Status: Live API Extraction Tested; Full Production Workflow Pending**

### Objective

Retrieve project listing information from Truelancer and convert it into structured project records.

### Implementation

The scraper supports:

- Truelancer HTML parsing.
- Truelancer structured JSON parsing.
- Extraction of project titles.
- Extraction of descriptions.
- Extraction of budgets and pricing information where available.
- Extraction of technology information where available.
- Extraction of project dates where available.
- Extraction of project URLs.
- Pagination support.
- Handling of missing or inconsistent fields.

### API Response Handling

The extraction implementation supports structured Truelancer project responses containing project data and pagination information.

The API response can provide a next-page URL, which the scraper validates before requesting the next page.

### Important Extraction Rules

- Only information actually present in the source response should be extracted.
- Missing values must remain missing rather than being fabricated.
- Project URLs must not be invented.
- Application URLs must not automatically be treated as original project listing URLs.
- Records without required original listing URLs must be excluded from submission to the backend.
- Pagination must remain restricted to supported Truelancer hosts.

### Expected Outcome

A reliable extraction process that converts Truelancer responses into standardized project records.

---

## 5. Pagination and Multi-Page Extraction

**Status: Implemented and Targeted Tests Passed**

### Objective

Retrieve projects across multiple listing pages instead of processing only the first page.

### Implementation

- Extract the next-page URL from the response.
- Validate the next-page URL.
- Confirm that the destination belongs to an allowed Truelancer host.
- Request the next page through the configured fetching provider.
- Parse the response using the appropriate HTML or JSON parser.
- Continue until there are no further pages or the configured page limit is reached.
- Handle failed page requests without corrupting previously extracted results.

### Supported Truelancer Hosts

- `truelancer.com`
- `www.truelancer.com`
- `api.truelancer.com`

The API host is included because the structured project response can provide pagination URLs pointing to that host.

### Verification

The pagination implementation has been tested with both HTML-based and structured JSON response scenarios.

The API host is accepted as a valid starting host after the corresponding validation update.

### Expected Outcome

A controlled multi-page extraction workflow with URL validation and error handling.

---

## 6. Data Processing Before API Submission

**Status: Core Implementation Completed**

### Objective

Ensure that extracted records are processed before they are sent to the backend.

### Processing Sequence

1. Retrieve the source response.
2. Parse the response.
3. Extract project information.
4. Clean extracted text.
5. Normalize project fields.
6. Validate required fields.
7. Classify the project.
8. Detect potential duplicates.
9. Prepare the backend payload.
10. Submit valid records through the API.

### Validation Rules

- Required fields must be present.
- Optional fields may remain empty when unavailable.
- Dates must be normalized where possible.
- URLs must be valid.
- Project types must follow the supported classification values.
- Invalid records must not be submitted.
- Records without original listing URLs must be skipped.

### Classification

The existing Python keyword-based classifier is used.

A second AI classification service is not part of the current design.

### Duplicate Detection

The existing deduplication implementation checks project information against existing records and identifies potential duplicates before insertion.

### Expected Outcome

Only valid and appropriately processed project records proceed to API submission.

---

## 7. Backend API Integration

**Status: Core Integration Implemented; Live End-to-End Verification Pending**

### Objective

Connect the scraping pipeline to the FastAPI backend.

### Main API Operations

The backend provides functionality for:

- Retrieving projects.
- Creating projects.
- Deleting projects.
- Retrieving and managing sources.
- Creating scraping-run records.
- Updating scraping-run status.

### Scraping-Run Tracking

The scraping workflow records execution information through the `scraping_runs` table.

The relevant fields include:

- `id`
- `source_id`
- `started_at`
- `completed_at`
- `status`
- `records_found`
- `error_log`

Supported run states include:

- `RUNNING`
- `SUCCESS`
- `FAILED`

### Verification Activities

- Verify backend connectivity.
- Verify API request and response formats.
- Verify authentication where required.
- Verify Supabase connectivity.
- Verify valid project insertion.
- Verify that invalid records are rejected or skipped appropriately.
- Verify scraping-run status updates.
- Verify that failed scraping runs are recorded correctly.

### Expected Outcome

A functioning connection between the scraper, FastAPI, and Supabase.

---

## 8. Supabase Database Verification

**Status: Database Integration Implemented; Complete Live Insertion Verification Pending**

### Objective

Verify that processed project records are stored correctly in Supabase.

### Verification Activities

- Confirm the Supabase project configuration.
- Verify database connectivity.
- Verify required database tables.
- Verify project field mapping.
- Verify date and URL formats.
- Verify classification fields.
- Verify duplicate-related fields.
- Verify source relationships.
- Verify scraping-run records.
- Verify that invalid or duplicate records are not inserted unnecessarily.

### Important Database Fields

The project mapping includes fields such as:

- Project title
- Description
- Budget
- Pricing type
- Posted date
- Deadline
- Required technologies
- Project type
- Source information
- Original URL
- Category
- Confidence score
- Duplicate status
- Content hash

The final stored values depend on the available source information and database schema.

### Expected Outcome

Reliable storage of standardized project information in Supabase.

---

## 9. Frontend Integration

**Status: Initial Integration Available; Full Live Data Verification Pending**

### Objective

Display projects collected through the live scraping workflow in the React dashboard.

### Activities

- Verify frontend API configuration.
- Verify communication with the backend.
- Retrieve projects from the backend.
- Display project details.
- Display project source information.
- Provide access to original project URLs.
- Verify search functionality.
- Verify filtering functionality.
- Verify empty and error states.
- Verify that newly collected projects appear in the dashboard.

### Expected Outcome

A dashboard that displays the latest successfully stored project information.

---

## 10. Scheduler and Automated Scraping

**Status: Implemented; Disabled by Default**

### Objective

Support automatic scraping at configured intervals.

### Implementation

- APScheduler integration is available.
- Scheduler startup is connected to the FastAPI application lifecycle.
- Scheduler configuration is controlled through environment variables.
- Scheduled execution is disabled by default.

### Configuration

The current default configuration is:

`SCHEDULER_ENABLED=false`

### Verification Activities

- Verify scheduler initialization.
- Verify the configured execution interval.
- Verify that scheduled execution invokes the intended scraping workflow.
- Verify that each execution creates a scraping-run record.
- Verify successful and failed execution logging.
- Verify that repeated executions do not unnecessarily insert duplicate projects.
- Verify the deployment environment can support the scheduler reliably.

### Activation Condition

Scheduled scraping should only be enabled after the complete live scraping-to-database workflow has been verified.

### Expected Outcome

A controlled automated scraping process that can operate reliably in the deployment environment.

---

## 11. Testing and Validation

**Status: Targeted Integration Testing Completed; Complete Production Validation Pending**

### Objective

Verify the fetching, extraction, processing, API integration, and database workflow.

### Testing Areas

**Fetching Tests**

- Provider configuration.
- ScraperAPI request handling.
- Successful responses.
- Failed responses.
- Timeout handling.

**Extraction Tests**

- HTML parsing.
- JSON parsing.
- Required-field extraction.
- Missing-field handling.
- URL extraction.

**Pagination Tests**

- Next-page URL extraction.
- Allowed-host validation.
- API-host starting URL validation.
- Multi-page extraction.
- Pagination failure handling.

**Processing Tests**

- Data cleaning.
- Field validation.
- Classification.
- Duplicate detection.
- Missing URL handling.

**Backend Tests**

- API connectivity.
- Project submission.
- Database mapping.
- Scraping-run logging.
- Error handling.

**Frontend Tests**

- Project retrieval.
- Project display.
- Search.
- Filtering.
- Export.

### Current Test Result

The following targeted test files were executed together:

- `tests/test_end_to_end_scraperapi_integration.py`
- `tests/test_scraper.py`
- `tests/test_pipeline.py`
- `tests/test_pagination_and_logging.py`

**Result: 70 tests passed in 1.08 seconds.**

This result confirms that the selected test cases passed. It does not establish that the complete production workflow has already been verified.

---

## 12. Production Deployment Verification

**Status: Pending Final Verification**

### Objective

Verify that all application components work together in the intended deployment environment.

### Activities

- Verify backend deployment.
- Verify frontend deployment.
- Verify production environment variables.
- Verify ScraperAPI configuration in the deployment environment.
- Verify Supabase connectivity.
- Verify backend API accessibility.
- Verify frontend-to-backend communication.
- Execute a controlled live extraction.
- Verify project processing.
- Verify project insertion into Supabase.
- Verify project retrieval through the backend API.
- Verify project display in the frontend dashboard.
- Verify scraping-run logging.
- Verify error handling.
- Verify scheduler configuration.

### Expected Outcome

A working deployed application that can retrieve, process, store, and display freelance project opportunities.

---

## 13. Final End-to-End Workflow

The final verified workflow should follow this sequence:

### Step 1 – Fetching

The scraper sends a request through the configured ScraperAPI provider to retrieve Truelancer project listing information.

### Step 2 – Extraction

The scraper parses the response and extracts the available project details.

### Step 3 – Pagination

The scraper follows validated next-page URLs to retrieve additional project listings.

### Step 4 – Cleaning and Validation

The extraction layer cleans and validates the collected project information.

### Step 5 – Classification

The keyword-based classifier identifies the relevant project category and project type.

### Step 6 – Duplicate Detection

The deduplication module checks whether the project already exists or is likely to be a duplicate.

### Step 7 – API Submission

Valid, non-duplicate records are prepared and submitted to the FastAPI backend.

### Step 8 – Database Storage

The backend stores the project records in Supabase.

### Step 9 – Dashboard Display

The React frontend retrieves the stored project records through the backend API and displays them.

### Step 10 – Monitoring

The scraping-run tracking system records execution status and relevant errors.

### Step 11 – Automation

After successful production verification, scheduled scraping can be enabled.

---

## 14. Remaining Implementation Priorities

The remaining work should be completed in the following order:

### Priority 1 – Complete Live Scraping Verification

Verify the complete configured ScraperAPI fetching and Truelancer extraction workflow.

### Priority 2 – Verify API Submission

Confirm that extracted and processed records can be submitted successfully to FastAPI.

### Priority 3 – Verify Supabase Storage

Confirm that valid project records are inserted and mapped correctly.

### Priority 4 – Verify Frontend Integration

Confirm that newly collected records are displayed correctly in the dashboard.

### Priority 5 – Complete Full-System Testing

Run the complete relevant backend and frontend test suites and resolve any outstanding failures.

### Priority 6 – Verify Production Configuration

Check deployment environment variables, API accessibility, database connectivity, and error logging.

### Priority 7 – Verify Scheduled Execution

Test scheduler behavior in the deployment environment before enabling automatic execution.

---

## 15. Completion Criteria

The live scraping and deployment workflow will be considered complete when:

- ScraperAPI is configured correctly in the target environment.
- Truelancer project listings can be retrieved successfully.
- Multiple listing pages can be processed.
- Extracted records are correctly cleaned and validated.
- Classification works as expected.
- Duplicate detection works as expected.
- Invalid records are not submitted.
- Valid records are successfully submitted to FastAPI.
- Supabase stores the records correctly.
- Scraping-run information is recorded.
- The frontend displays newly collected projects.
- Search and filtering work with the collected data.
- Export functionality works correctly.
- Production configuration is verified.
- The complete workflow passes end-to-end testing.
- Scheduled scraping is tested before being enabled.

---

## 16. Final Expected Result

The final objective is to establish a working live data pipeline in which ScrapeScout automatically retrieves freelance project opportunities from the configured freelancing source, processes and classifies the extracted information, prevents unnecessary duplicate entries, stores valid records in Supabase, and makes those records accessible through the FastAPI backend and React dashboard.

The initial release will focus on a stable Truelancer integration. Additional freelancing platforms can be integrated later using the same reusable fetching, extraction, validation, classification, and storage architecture.

---

## 17. Manual Fetch, Recurring Scheduler & Frontend Integration Update

- **Manual Fetch Endpoint:** `POST /scrape/truelancer/manual` (authenticated via `require_authenticated`) invokes `run_truelancer_pipeline()` for the active `Truelancer` source using `SCRAPING_PROVIDER` (`scraperapi` / `direct`), `SCHEDULER_MAX_PAGES`, and `SCHEDULER_MIN_REQUEST_INTERVAL`.
- **Persistent Recurring Scheduler:** `GET/POST /schedules`, `PATCH/DELETE /schedules/{id}`, `POST /schedules/{id}/pause|resume`, and `GET /schedules/status` manage persistent daily, weekly, monthly, and custom schedules in `public.scraping_schedules` (`migrations/05_scraping_schedules.sql`) with `Asia/Kolkata` default timezone, APScheduler overlap protection, and real calculated `next_run_at` timestamps.
- **Source Mapping & Analytics:** `GET /analytics/dashboard` filters `sources` by `is_active = True` and reports `inserted_today`, `duplicates_skipped`, `active_sources_count`, and `upcoming_schedules`. Safe SQL cleanup & backfill for legacy `NULL` `source_id` Truelancer projects is prepared in `migrations/04_source_cleanup_and_backfill.sql` for manual review and execution.
- **Frontend Workflow:** The multi-page React UI (`Dashboard`, `Projects`, `Sources`, `Scheduler`, `Scraping Activity`, `Exports`, `Settings`) provides a **Fetch from Truelancer** button for all authenticated users, a full **Scheduler** management UI, and persistent Light/Dark mode.
- **Live Verification Note:** Automated backend (`pytest`) and frontend (`jest`) suites use mocked requests and do not constitute a live Truelancer scraping run or live scheduled run against Truelancer. Live verification remains pending explicit execution against the target environment.

- **Manual Fetch Endpoint:** `POST /scrape/truelancer/manual` (admin-protected via `require_admin`) invokes `run_truelancer_pipeline()` for the active `Truelancer` source using `SCRAPING_PROVIDER` (`scraperapi` / `direct`), `SCRAPER_API_KEY`, `SCHEDULER_MAX_PAGES`, and `SCHEDULER_MIN_REQUEST_INTERVAL`.
- **Source Mapping & Analytics:** `GET /analytics/dashboard` now filters `sources` by `is_active = True`. Safe SQL cleanup & backfill for legacy `NULL` `source_id` Truelancer projects is prepared in `migrations/04_source_cleanup_and_backfill.sql` for manual review and execution.
- **Frontend Workflow:** The redesigned multi-page React UI (`Dashboard`, `Projects`, `Sources`, `Scraping Activity`, `Exports`, `Settings`) provides a **Fetch from Truelancer** button with loading feedback, result breakdown, automatic data refresh, and persistent Light/Dark mode.
- **Live Verification Note:** Automated backend (`pytest`) and frontend (`jest`) suites use mocked requests and do not constitute a live Truelancer scraping run. Live scraping verification remains pending explicit execution against the target environment.