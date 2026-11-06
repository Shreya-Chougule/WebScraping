# ScrapeScout – Web & App Project Discovery Tool

ScrapeScout is a project discovery system designed to collect genuine freelance opportunities related to websites, web applications, mobile applications, and software development from approved online platforms.

## Project Workflow

1. Data collection from approved freelance platforms.
2. Project data extraction and standardization.
3. Relevance classification.
4. Duplicate detection.
5. Database storage using Supabase and PostgreSQL.
6. Backend API development using FastAPI.
7. Frontend dashboard for discovering projects.

## Current Implementation

- Truelancer selected as the first data source.
- Truelancer HTML parser developed.
- Common project extraction schema created.
- JSON and CSV export functionality implemented.
- FastAPI endpoints configured.
- Supabase database integration tested.
- Python automated tests added.

**Current focus:** Phase 4 – First Data Source & Scraper, and Phase 5 – Data Extraction & Standardization.

## Technology Stack

- Python
- FastAPI
- React
- Supabase / PostgreSQL
- Requests and BeautifulSoup
- Pytest
- Git and GitHub

## Repository Structure

```text
WebScraping/
├── backend/
├── frontend/
├── tests/
├── test_data/
├── output/
├── README/
├── pytest.ini
├── .gitignore
└── README.md
```

## Backend Setup

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Configure the required Supabase environment variables in a local `.env` file.

Start the backend from the repository root:

```bash
python -m uvicorn main:app --app-dir backend --reload
```

Open API documentation at:

http://127.0.0.1:8000/docs

## Run Tests

```bash
python -m pytest -v
```

## Project Documentation

- [Project Roadmap](README/RoadMap.md)
- [Source Research](README/Source%20Research.md)
- [Requirement Analysis](README/requirement-analysis.docx)

## Responsible Data Collection

Scraping must respect platform terms of service, robots.txt policies, access restrictions, and applicable laws. The project does not intend to bypass authentication, CAPTCHAs, or other access controls.