# Phase 4–5 Implementation Documentation
## ScrapeScout – Project Discovery Tool

**Project:** ScrapeScout – EDI Web & App Project Discovery Tool  
**Phases Covered:** Phase 4 – First Data Source & Scraper; Phase 5 – Data Extraction & Standardization  
**Primary Data Source:** Truelancer  
**Implementation Language:** Python  
**Core Libraries:** Requests, BeautifulSoup, JSON, CSV  
**Backend Integration:** FastAPI and Supabase

---

## 1. Introduction

This document describes the implementation of Phase 4 and Phase 5 of the ScrapeScout Project Discovery Tool.

The objective of these phases is to collect publicly available freelance project listings from Truelancer and transform the collected information into structured, standardized records that can be used by the backend and database.

The implementation includes:

- Truelancer project listing extraction.
- HTML and embedded JSON parsing.
- Multi-page scraping with pagination.
- Data cleaning and standardization.
- Project URL validation and canonicalization.
- Project type inference.
- Project data validation.
- JSON and CSV export.
- Supabase field mapping.
- Scraping-run status tracking through the backend API.

The implementation is designed to preserve available project information while handling missing or invalid values safely.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main implementation language |
| Requests | HTTP requests to public webpages and backend APIs |
| BeautifulSoup | HTML parsing and text extraction |
| JSON | Parsing embedded listing data and exporting records |
| CSV | Exporting structured project data |
| Regular Expressions | Text normalization and field validation |
| FastAPI | Backend API integration and scraping-run logging |
| Supabase | Project data storage |
| Pytest | Automated testing |

## 3. Phase 4 – First Data Source & Scraper

### 3.1 Truelancer Source Integration

Truelancer was selected as the first data source for the project.

The scraper retrieves project listing information from publicly accessible Truelancer pages. The implementation uses Python Requests to retrieve webpage content and BeautifulSoup to parse HTML.

The main implementation files are:

- `backend/src/scraper.py`
- `backend/src/truelancer_parser.py`

### 3.2 HTTP Request Handling

The `fetch_page()` function handles webpage retrieval.

Its implementation includes:

- HTTP and HTTPS URL validation.
- Rejection of URLs containing embedded credentials.
- Validation of allowed standard HTTP/HTTPS ports.
- A configurable request timeout.
- A descriptive User-Agent header.
- Disabled automatic redirect following.
- Handling of HTTP 403 and 429 responses.
- Detection of HTTP redirects.
- Detection of common security checkpoint messages.

If a website restricts access or presents a security checkpoint, the scraper stops rather than attempting to bypass the restriction.

### 3.3 Truelancer Project Parsing

The `parse_truelancer_html()` function extracts project information from locally saved Truelancer HTML.

Truelancer listing data is obtained from the embedded `__NEXT_DATA__` script, which contains structured JSON.

The parser:

1. Loads the HTML using BeautifulSoup.
2. Locates the `__NEXT_DATA__` script.
3. Extracts and parses the embedded JSON.
4. Accesses the project records.
5. Processes each valid project record.
6. Creates standardized `ExtractedProject` objects.

Records without a usable title are skipped. Unexpected embedded-data structures produce descriptive errors.

### 3.4 Pagination

The scraper supports retrieving multiple pages of Truelancer listings.

The following functions implement pagination:

- `extract_next_page_url()`
- `validate_pagination_url()`
- `scrape_truelancer_pages()`

The pagination workflow:

1. Fetches the starting listing page.
2. Parses the available projects.
3. Extracts the next-page URL from embedded JSON.
4. Validates the next-page URL.
5. Waits for the configured request interval.
6. Fetches and parses the next page.
7. Stops when no next page is available or the configured page limit is reached.

The default maximum is three pages.

Pagination URLs must use HTTPS and remain on the same approved Truelancer hostname as the original URL. Unexpected hosts, ports, or URL structures are rejected.

A set of previously encountered project URLs is used to avoid collecting the same listing more than once across pages.

### 3.5 Scraping-Run Logging

The scraper integrates with the FastAPI backend to track scraping activity.

Three functions manage scraping-run records:

- `create_scraping_run()`
- `update_scraping_run()`
- `run_truelancer_scraping()`

The workflow is:

1. Create a scraping-run record with status `RUNNING`.
2. Execute the Truelancer pagination and extraction process.
3. Update the record to `SUCCESS` when scraping completes.
4. Store the number of records found.
5. If scraping fails, update the record to `FAILED` and store an error description.

The implementation uses POST requests to create runs and PATCH requests to update their status.

The fetcher and sleep-function parameters also allow local tests to simulate scraping without making live website requests.

## 4. Phase 5 – Data Extraction & Standardization

### 4.1 Standardized Project Data Model

The `ExtractedProject` dataclass in `backend/src/extraction_schema.py` defines the standardized structure used for extracted project records.

The fields include:

| Field | Description |
|---|---|
| `title` | Project title |
| `description` | Project description |
| `budget` | Available project budget |
| `currency` | Currency code |
| `posted_date` | Project posting date |
| `deadline` | Project deadline, when available |
| `technologies` | Required technologies or skills |
| `project_type` | Web, Mobile App, Software, or Both |
| `source_name` | Name of the source platform |
| `original_url` | Original project listing URL |
| `pricing_type` | Pricing or job type |
| `client_name` | Client name, when available |
| `location` | Client or project location, when available |
| `contact_info` | Contact information, when available |
| `category` | Classification category |
| `confidence_score` | Classification confidence score |
| `is_relevant` | Internal relevance flag |

Optional fields are represented using Python's optional types. Missing information is not fabricated.

### 4.2 Data Extraction

The parser extracts available information from Truelancer's embedded project records.

The extracted information includes:

- Project title.
- Description.
- Budget.
- Currency.
- Posting date.
- Required skills and technologies.
- Original project URL.
- Pricing type.
- Country or location.
- Project type.

The parser processes records individually and skips invalid records where required information, such as the title, is unavailable.

### 4.3 Data Cleaning

The `clean_text()` function removes unwanted HTML markup and normalizes extracted text.

Cleaning operations include:

- HTML tag removal.
- HTML entity decoding.
- Whitespace normalization.
- Removal of unnecessary line breaks and repeated spaces.
- Basic sentence-spacing normalization.
- Conversion of empty cleaned values to `None`.

This helps maintain consistent text fields across extracted records.

### 4.4 Technology Extraction

The parser extracts technology and skill information from Truelancer's structured `skills` data.

It:

1. Checks whether the skills field contains a list.
2. Reads the available skill names.
3. Cleans each skill value.
4. Ignores invalid or empty entries.
5. Removes duplicate technology names while preserving their order.

The resulting technologies are stored as a list of strings.

### 4.5 Date and Currency Standardization

Posting dates are extracted from the source's `created_at` field.

When the date begins with a valid `YYYY-MM-DD` pattern, that date portion is retained.

Currency values are cleaned and converted to uppercase.

The implementation does not invent missing dates or currency values. Missing information remains `None`.

The Supabase mapper converts valid `YYYY-MM-DD` dates into ISO datetime strings before database submission.

### 4.6 Project Type Inference

The Truelancer parser uses `infer_truelancer_project_type()` to infer the likely project type.

Supported values include:

- `Web`
- `Mobile App`
- `Software`
- `Both`

The function uses keyword patterns and contextual checks.

Strong evidence in the project title receives priority. When the title does not provide sufficient information, the description is checked for explicit development or creation requirements.

If the available information is insufficient, the project type remains `None` rather than being guessed.

### 4.7 URL Canonicalization

The `canonicalize_url()` function normalizes Truelancer project listing URLs.

It:

- Accepts approved Truelancer hostnames.
- Requires the expected freelance-project URL path.
- Uses HTTPS as the canonical scheme.
- Removes trailing slashes.
- Removes query strings and fragments.
- Normalizes hostname and path casing.

Canonical URLs are used to identify duplicate listings during extraction.

Invalid or unexpected project URLs are not retained as valid canonical project links.

### 4.8 Project Data Validation

The module `backend/src/project_validator.py` provides independent validation functions.

The main functions are:

- `is_valid_date()`
- `is_valid_url()`
- `validate_project()`
- `validate_projects()`

Validation checks include:

- Required project title.
- Required source name.
- Required original URL.
- Valid HTTP/HTTPS URL structure.
- Valid `YYYY-MM-DD` dates.
- Three-letter uppercase currency codes.
- Supported project type values.
- Correct technologies list structure.
- Valid optional text fields.

The validator returns a list of validation errors for an individual project.

For multiple projects, `validate_projects()` returns a dictionary containing the indexes and validation errors of invalid records.

**Implementation note:** This validation module is implemented and tested as a separate utility. It is not currently called directly by the scraper workflow.

## 5. Data Export

The extraction schema supports exporting project records into JSON and CSV formats.

The functions are:

- `save_projects_json()`
- `save_projects_csv()`

The `export_projects()` function in `backend/src/scraper.py` uses these functions to save the extracted records.

Default output files:

- `output/projects.json`
- `output/projects.csv`

JSON export preserves structured data, including technology lists.

CSV export converts technology lists into comma-separated text and writes a header containing the standardized project fields.

UTF-8 encoding is used for file output, with a UTF-8 BOM for CSV compatibility with common spreadsheet applications.

## 6. Supabase Field Mapping

The `map_project_to_supabase()` function in `backend/src/supabase_mapper.py` converts an `ExtractedProject` object into the payload expected by the backend's project API and database mapping.

The mapping includes:

- Title and description.
- Budget and currency.
- Posting date and deadline.
- Required technologies.
- Project type.
- Source ID.
- Original project URL.
- Client name.
- Location.
- Contact information.
- Category and confidence score.

The source name is resolved against the backend sources endpoint to obtain the corresponding source ID.

Missing values represented by `Not specified` are converted to `None` for relevant database fields.

The `is_relevant` flag is an internal processing field and is not included in the Supabase payload.

The mapper prepares the payload; actual database insertion is handled through the backend API.

## 7. Overall Implementation Workflow

The Phase 4–5 data collection and processing workflow is summarized below.

1. Select the Truelancer listing source.
2. Retrieve publicly accessible page content.
3. Parse the embedded project data.
4. Extract project fields.
5. Clean and standardize available values.
6. Infer the project type where sufficient evidence exists.
7. Normalize project URLs.
8. Remove repeated listing URLs.
9. Create standardized `ExtractedProject` records.
10. Export records to JSON or CSV when requested.
11. Map records into the backend project payload when API submission is requested.

Scraping-run logging is available through the FastAPI integration.

The extraction, export, and API submission functions are separate operations; they should not be interpreted as one automatically triggered workflow.

## 8. Testing and Verification

Automated tests are maintained under the `tests/` directory.

The Phase 4–5 related test modules include:

- `tests/test_scraper.py`
- `tests/test_truelancer_parser.py`
- `tests/test_extraction_schema.py`
- `tests/test_project_validator.py`
- `tests/test_supabase_mapper.py`
- `tests/test_pagination_and_logging.py`

Testing covers:

- HTML and embedded JSON parsing.
- Project field extraction.
- Missing and invalid values.
- Text cleaning.
- Project type inference.
- URL validation and canonicalization.
- Duplicate listing URL handling.
- Pagination behavior.
- Scraping-run creation and status updates.
- JSON and CSV export.
- Supabase payload mapping.
- Project validation.

**Verification status:** The Phase 4–5 targeted test suite was executed locally, and all tests passed.

The tests use local fixtures and mocks where appropriate, avoiding the need for live Truelancer requests during routine development testing.

## 9. Limitations and Future Improvements

The current implementation provides the initial Truelancer data collection and standardization workflow. The following improvements may be considered:

1. Add more approved freelance project sources.
2. Introduce source-specific parser configurations for easier extension.
3. Integrate project validation directly into the extraction or API submission workflow.
4. Add stronger monitoring and recovery for failed scraping runs.
5. Improve handling of source-side HTML or embedded JSON structure changes.
6. Add more comprehensive URL normalization and source-specific duplicate checks.
7. Verify the complete live scraping-to-database workflow under permitted access conditions.
8. Improve scheduling and automation in the subsequent pipeline phase.

The scraper does not bypass security checkpoints, access restrictions, or website protections.

## 10. Conclusion

Phase 4 established Truelancer as the first integrated data source and implemented the initial scraper, pagination, request handling, and scraping-run logging.

Phase 5 established a standardized project data model and implemented extraction, cleaning, field normalization, validation utilities, export functionality, and Supabase payload mapping.

Together, these phases provide the foundation for the subsequent classification, duplicate detection, automated pipeline, API, and dashboard components of ScrapeScout.

---

**Document:** Phase 4–5 Implementation Documentation  
**Project:** ScrapeScout – Project Discovery Tool  
**Status:** Implementation and targeted automated tests completed locally.