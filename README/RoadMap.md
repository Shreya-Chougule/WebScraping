# ScrapeScout – Project Development Roadmap

## 1. Project Overview

ScrapeScout is a web and mobile application project discovery tool designed to collect freelance project opportunities from selected freelancing platforms, extract relevant information, classify projects, identify duplicates, and make the collected data accessible through a centralized dashboard.

The system is designed to help users discover relevant freelance opportunities without manually visiting multiple freelancing platforms.

### 1.1 Main Objectives

- Collect freelance project listings from selected freelancing platforms.
- Extract and standardize project information.
- Classify projects based on their technology requirements and project type.
- Identify duplicate project listings.
- Store structured project data in a centralized database.
- Provide APIs for accessing and managing collected projects.
- Display project information through a dashboard.
- Support searching, filtering, and exporting project data.
- Support scheduled data collection.

### 1.2 Initial Data Sources

The project focuses exclusively on freelancing platforms.

The initial list of potential sources includes:

1. Truelancer
2. PeoplePerHour
3. Guru
4. Freelancer.com
5. Malt

Truelancer is the initial implementation source. Additional platforms can be integrated in later stages after their technical compatibility is evaluated.

### 1.3 Standard Project Information

The system aims to collect the following fields:

- Project title
- Project description
- Budget
- Pricing type
- Posted date
- Deadline
- Required technologies
- Project type
- Client name, when available
- Client location, when available
- Source platform
- Original project URL
- Project category
- Classification confidence
- Duplicate status

The availability of individual fields depends on the information provided by each source.

---

## 2. System Architecture

The overall system follows this workflow:

**Freelancing Platforms → Website Fetching → Data Extraction → Data Cleaning and Validation → Classification → Duplicate Detection → Database Storage → Backend APIs → Frontend Dashboard**

### 2.1 Website Fetching

The scraper retrieves publicly accessible project listing information from the selected freelancing platforms.

ScraperAPI has been integrated as a website-fetching provider. The provider is configured through environment variables so that the fetching implementation can be reused across supported sources.

### 2.2 Data Extraction

The extraction layer parses the retrieved website content and extracts structured project information.

### 2.3 Data Processing

Extracted information is cleaned, validated, standardized, classified, and checked for duplicates.

### 2.4 Database

Supabase with PostgreSQL is used for centralized storage.

### 2.5 Backend

FastAPI provides endpoints for project retrieval, insertion, deletion, source management, scraping-run tracking, and other application operations.

### 2.6 Frontend

The React dashboard provides an interface for viewing and managing collected project opportunities.

---

## 3. Development Phases

## Phase 1 – Requirement Analysis and Project Planning

**Status: Completed**

### Objectives

Understand the project requirements, identify the target users, define the system scope, and establish the initial technical direction.

### Activities

- Analyze the project requirements.
- Identify the main problem and proposed solution.
- Define the expected system functionality.
- Identify the initial freelancing platforms.
- Define the required project information fields.
- Establish the overall project architecture.
- Divide responsibilities among team members.

### Expected Outcome

A clear project scope, requirement document, initial architecture, and development plan.

---

## Phase 2 – Database Design and Backend Foundation

**Status: Completed**

### Objectives

Establish the database structure and backend foundation required for the project.

### Activities

- Set up the Supabase project.
- Configure PostgreSQL database connectivity.
- Design the initial database tables.
- Establish the FastAPI backend.
- Configure environment variables.
- Implement basic database connectivity.
- Create foundational backend endpoints.

### Main Database Entities

- Users
- Sources
- Projects
- Scraping Runs
- Duplicate Records
- Keywords

### Expected Outcome

A functional backend foundation connected to the Supabase database.

---

## Phase 3 – Frontend Foundation and Application Integration

**Status: Initial Implementation Completed**

### Objectives

Establish the frontend application structure and its communication with the backend.

### Activities

- Set up the React frontend.
- Establish the frontend project structure.
- Connect the frontend with backend APIs.
- Implement the initial dashboard layout.
- Display project information retrieved from the backend.
- Establish the basic application flow.

### Expected Outcome

An initial frontend application capable of communicating with the backend.

---

## Phase 4 – Website Research, Fetching, and Data Extraction

**Status: Core Truelancer Implementation Completed; Further Source Integration Pending**

### Objectives

Develop the website-fetching and extraction functionality for collecting freelance project listings.

### Activities

- Research the structure of selected freelancing platforms.
- Evaluate the technical feasibility of extracting project information.
- Implement the initial Truelancer extraction workflow.
- Develop HTML and JSON parsing functionality.
- Extract project titles and descriptions.
- Extract budgets and pricing information when available.
- Extract project dates and technology requirements when available.
- Extract original project URLs.
- Implement pagination support.
- Handle missing and inconsistent information.
- Introduce safe fetching and response validation.
- Integrate ScraperAPI as a configurable fetching provider.
- Implement local test fixtures for repeatable extraction testing.

### Important Implementation Details

- Truelancer extraction supports structured JSON responses and HTML-based project data.
- Pagination support allows the scraper to follow the next-page URL.
- The scraper validates pagination URLs before requesting subsequent pages.
- The fetching provider is selected through configuration.
- Missing project URLs are not fabricated.
- Records without required original project URLs are excluded from API submission.

### Expected Outcome

A reusable extraction pipeline capable of collecting structured freelance project information from the initial source.

---

## Phase 5 – Data Cleaning, Validation, and Standardization

**Status: Core Implementation Completed**

### Objectives

Ensure that extracted project information is consistent, structured, and suitable for database storage.

### Activities

- Remove unnecessary HTML markup.
- Decode HTML entities.
- Normalize whitespace.
- Standardize project information.
- Validate extracted fields.
- Handle missing optional fields.
- Normalize project URLs.
- Standardize dates where possible.
- Map extracted information to the database schema.
- Validate records before API submission.
- Generate structured JSON and CSV output where required.

### Expected Outcome

Clean and validated project records ready for classification and database insertion.

---

## Phase 6 – Project Classification

**Status: Core Implementation Completed**

### Objectives

Automatically categorize extracted projects based on their descriptions and requirements.

### Activities

- Develop the keyword-based classification system.
- Identify relevant technologies and keywords.
- Classify projects into supported project categories.
- Determine project types such as Web, Mobile App, Software, Both, or None where applicable.
- Generate classification confidence information.
- Handle ambiguous or insufficient project descriptions.
- Integrate classification into the extraction workflow.

### Implementation Decision

The project uses the existing Python keyword-based classifier.

A second AI classification layer is not included in the current implementation because it would duplicate classification work and introduce unnecessary complexity.

### Expected Outcome

Automatically classified project records with relevant category and project-type information.

---

## Phase 7 – Duplicate Detection

**Status: Core Implementation Completed**

### Objectives

Prevent duplicate project listings from unnecessarily entering the database.

### Activities

- Develop the project deduplication module.
- Normalize project information before comparison.
- Compare project URLs and relevant project content.
- Generate content hashes where applicable.
- Use similarity matching for identifying potentially duplicated records.
- Check existing records before insertion.
- Maintain duplicate-related information.
- Integrate duplicate detection into the scraping workflow.

### Expected Outcome

A deduplication mechanism that reduces repeated project records and maintains cleaner database information.

---

## Phase 8 – Scraping Pipeline and Automation

**Status: Core Pipeline Implemented; Production Automation Verification Pending**

### Objectives

Connect all scraping and data-processing components into a reusable workflow.

### Activities

- Integrate website fetching with extraction.
- Integrate extraction with validation.
- Integrate classification and deduplication.
- Connect processed records with backend APIs.
- Implement scraping-run tracking.
- Record run status, start time, completion time, and errors.
- Handle fetching and processing failures.
- Configure the scraping provider through environment variables.
- Implement scheduler support.
- Keep scheduled execution disabled by default until production verification is complete.

### Expected Outcome

An integrated scraping pipeline capable of executing the complete data-processing workflow and recording its execution status.

---

## Phase 9 – Backend API Development and Integration

**Status: Core Implementation Completed; Production End-to-End Verification Pending**

### Objectives

Provide backend endpoints for interacting with project data and managing scraping operations.

### Activities

- Implement project retrieval endpoints.
- Implement project insertion endpoints.
- Implement project deletion functionality.
- Implement source management endpoints.
- Implement scraping-run creation and update endpoints.
- Integrate the backend with Supabase.
- Implement request validation.
- Handle API errors.
- Connect frontend operations with backend endpoints.
- Verify API responses and database connectivity.

### Expected Outcome

A functional backend API layer supporting the frontend and scraping pipeline.

---

## Phase 10 – Dashboard Development

**Responsibility: Frontend Team Member**

**Status: Initial Dashboard Implementation Available; Final Integration Review Pending**

### Objectives

Develop a dashboard that displays collected freelance opportunities in a clear and accessible format.

### Activities

- Develop the dashboard interface.
- Display collected projects.
- Show relevant project details.
- Provide navigation between dashboard sections.
- Add project links.
- Display useful project statistics where supported.
- Handle loading, empty, and error states.
- Ensure compatibility with backend API responses.

### Expected Outcome

A functional dashboard for viewing collected freelance opportunities.

---

## Phase 11 – Search and Filtering

**Responsibility: Frontend Team Member**

**Status: Initial Implementation Available; Final Verification Pending**

### Objectives

Allow users to find relevant projects efficiently.

### Activities

- Implement project search.
- Add keyword-based filtering.
- Add source-platform filtering.
- Add project-type filtering.
- Add technology-based filtering where supported.
- Support combinations of filters.
- Ensure filtering works with the backend data.
- Handle empty search results.

### Expected Outcome

A dashboard that allows users to locate relevant freelance projects using search and filters.

---

## Phase 12 – Data Export

**Responsibility: Frontend Team Member**

**Status: Implementation and Integration Verification Pending**

### Objectives

Allow users to export collected project information for external use.

### Activities

- Implement CSV export.
- Implement Excel export where supported.
- Include relevant project fields.
- Ensure exported records follow the standardized data structure.
- Support exporting filtered results where applicable.
- Validate generated files.

### Expected Outcome

A working data-export feature for collected project opportunities.

---

## Phase 13 – Security, Reliability, and Quality Review

**Status: Further Review Pending**

### Objectives

Improve the reliability and maintainability of the complete application.

### Activities

- Review backend API security.
- Verify authentication and authorization behavior.
- Review environment-variable handling.
- Verify that sensitive credentials are not exposed.
- Review database access and permissions.
- Test invalid and incomplete requests.
- Verify error handling.
- Review frontend and backend integration.
- Identify and fix critical bugs.
- Review application performance.
- Verify that scraping failures are recorded correctly.

### Expected Outcome

A more reliable application with appropriate security and error-handling mechanisms.

---

## Phase 14 – Testing and Validation

**Status: Targeted Testing Completed; Full System Validation Pending**

### Objectives

Verify that individual modules and the complete application behave as expected.

### Activities

- Run unit tests for extraction.
- Test pagination.
- Test ScraperAPI integration.
- Test project validation.
- Test classification.
- Test duplicate detection.
- Test API integration.
- Test scraping-run logging.
- Test frontend functionality.
- Test search and filtering.
- Test data export.
- Perform integration testing.
- Perform end-to-end testing.
- Resolve identified defects.

### Current Testing Evidence

A targeted backend test batch covering ScraperAPI integration, scraper functionality, pipeline functionality, and pagination/logging completed successfully:

**70 tests passed.**

This result applies to the selected test files and should not be treated as a complete full-project test-suite result.

### Expected Outcome

Verified individual modules and a validated end-to-end application workflow.

---

## Phase 15 – Deployment and Production Verification

**Status: Pending Final Verification**

### Objectives

Prepare and verify the complete application for its intended deployment environment.

### Activities

- Verify backend hosting configuration.
- Verify frontend deployment configuration.
- Configure production environment variables.
- Verify Supabase production connectivity.
- Verify API accessibility.
- Verify frontend-to-backend communication.
- Test the configured ScraperAPI provider in the deployment environment.
- Perform controlled live extraction tests.
- Verify project insertion into the database.
- Verify dashboard display of newly collected records.
- Verify scheduler configuration.
- Enable scheduled scraping only after the complete workflow is verified.
- Monitor application logs and errors.

### Expected Outcome

A deployed and verified application capable of collecting, processing, storing, and displaying freelance project opportunities.

---

## 4. Current Implementation Summary

The project has progressed through its core development stages.

### Implemented Components

- Requirement analysis and initial architecture.
- Supabase database foundation.
- FastAPI backend.
- React frontend foundation.
- Truelancer HTML and JSON extraction.
- Pagination support.
- ScraperAPI provider integration.
- Data cleaning and validation.
- Database field mapping.
- Keyword-based project classification.
- Duplicate detection.
- Scraping pipeline integration.
- Scraping-run logging.
- Backend project and source APIs.
- Scheduler implementation, disabled by default.
- Targeted automated testing.

### Current Testing Result

The latest reported targeted test batch completed with 70 passing tests.

### Remaining Major Activities

- Verify the complete live scraping-to-database workflow.
- Verify production API and frontend integration.
- Complete dashboard and filtering review.
- Complete CSV and Excel export verification.
- Complete security and reliability review.
- Perform full-system end-to-end testing.
- Complete deployment verification.
- Verify scheduled scraping before enabling it.

---

## 5. Future Enhancements

The following improvements may be considered after the initial application is stable:

- Integration of additional freelancing platforms.
- Improved project relevance filtering.
- More advanced technology matching.
- Additional project analytics.
- Improved duplicate detection.
- More detailed scraping history.
- Additional export formats.
- User-specific project preferences.
- Improved dashboard visualizations.

These enhancements are outside the immediate priority of completing and verifying the initial application.

---

## 6. Final Project Workflow

The intended final workflow is:

1. The configured scraper retrieves project listing information from a supported freelancing platform.
2. The extraction module parses the retrieved content.
3. The cleaning and validation layer standardizes the extracted records.
4. The classifier identifies project categories and types.
5. The deduplication module checks for repeated records.
6. Valid, non-duplicate records are submitted to the backend.
7. The backend stores the records in Supabase.
8. The frontend retrieves and displays project information.
9. Users search, filter, and explore the available projects.
10. Users export relevant project information when required.
11. Scheduled scraping can execute the workflow after production verification.

---

## 7. Project Completion Criteria

ScrapeScout will be considered ready for its initial release when:

- The initial freelancing source can be fetched reliably through the configured provider.
- Project information is extracted and standardized correctly.
- Classification and duplicate detection work as expected.
- Valid records are stored in Supabase.
- Backend APIs return the expected data.
- The frontend displays the collected projects correctly.
- Search and filtering work correctly.
- Export functionality produces valid files.
- Authentication and access controls are verified.
- The complete application passes end-to-end testing.
- Deployment configuration is verified.
- Scheduled scraping is tested before being enabled.

**Final Goal:** Deliver a functional freelance project discovery platform that automates the collection, processing, classification, storage, and presentation of relevant freelance opportunities.

---

## 8. Recent Implementation Update (Auth, Recurring Scheduler, Sources & Dynamic Analytics)

### Implemented Features
- **Manual Truelancer Fetch (`POST /scrape/truelancer/manual`):**
  - Protected with `require_authenticated` in `backend/main.py` (`trigger_manual_truelancer_fetch`), allowing any authenticated user (both `admin` and `viewer`) to trigger on-demand fetching while denying unauthenticated requests (`401`). Admin-only operations (`DELETE /projects/{id}`, `POST /notifications`, user/source management) remain protected with `require_admin`.
  - Resolves the active `Truelancer` source in Supabase, invokes `run_truelancer_pipeline()` from `backend/src/pipeline.py` using the configured `SCRAPING_PROVIDER` (`scraperapi` or `direct`), records `scraping_runs` (`RUNNING` -> `SUCCESS`/`FAILED`), classifies with the existing Python keyword classifier, deduplicates, assigns `source_id`, and returns full submission counts (`records_found`, `inserted`, `duplicate_skipped`, `irrelevant_skipped`, `missing_url_skipped`, `invalid_skipped`, `failed`).
- **Persistent Recurring Scheduler (`backend/src/scheduler.py`, `migrations/05_scraping_schedules.sql`):**
  - Supports **Daily**, **Weekly** (selected weekdays), **Monthly** (day of month), and **Custom** (5-field cron expression or minute interval) schedules with `Asia/Kolkata` default timezone.
  - Endpoints: `GET /schedules/status`, `GET /schedules`, `POST /schedules`, `PATCH /schedules/{id}`, `POST /schedules/{id}/pause`, `POST /schedules/{id}/resume`, `DELETE /schedules/{id}`.
  - Uses APScheduler `CronTrigger` / `IntervalTrigger`, `max_instances=1`, `coalesce=True`, `misfire_grace_time=300`, and a threading execution lock (`run_with_overlap_guard`) to prevent overlapping runs.
  - Calculates real `next_run_at` timestamps via APScheduler triggers (never fabricated). Keeps live background execution disabled (`SCHEDULER_ENABLED=false`) until explicitly enabled.
- **Dynamic Dashboard Analytics & Sources Cleanup:**
  - `GET /analytics/dashboard` filters `sources` by `is_active = True` and returns dynamic `total_projects`, `projects_today` (`Asia/Kolkata`), `inserted_today`, `duplicates_skipped`, `active_sources_count`, `scraping_runs`, `scheduler_enabled`, and `upcoming_schedules`.
  - Reversible SQL migrations: `migrations/04_source_cleanup_and_backfill.sql` (inactive placeholder sources & Truelancer `source_id` backfill) and `migrations/05_scraping_schedules.sql` (`scraping_schedules` table). Neither has been auto-executed.
- **Multi-Page SaaS Frontend & Scheduler UI (`frontend/src/App.js`, `frontend/src/App.css`):**
  - 7-section sidebar workspace: **Dashboard**, **Projects**, **Sources**, **Scheduler**, **Scraping Activity**, **Exports**, and **Settings**, with persistent Light/Dark mode (`scrapescout_theme`).
  - **Sources** displays only genuine active sources from Supabase plus clearly labeled **Planned · Not Connected** platforms (`Guru`, `PeoplePerHour`, `Freelancer.com`, `Malt`).

### Verification & Remaining Work
- **Automated Tests:** Backend `pytest` suite and frontend Jest suite pass using mocked HTTP/database interactions. Frontend production build (`npm run build`) verified.
- **Remaining / Pending:**
  - Review and execute `migrations/04_source_cleanup_and_backfill.sql` and `migrations/05_scraping_schedules.sql` in the Supabase SQL Editor.
  - Perform a controlled live Truelancer fetch test with `SCRAPER_API_KEY` against production/staging Supabase.
  - Enable `SCHEDULER_ENABLED=true` only after live scraping is verified and approved.
  - Implement source-specific parsers for planned platforms (`Guru`, `PeoplePerHour`, `Freelancer.com`, `Malt`) when approved.