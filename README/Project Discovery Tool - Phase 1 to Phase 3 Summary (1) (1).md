## Project Discovery Tool

## Technical Execution & Phase Progress Document

## Executive Summary

This document provides a comprehensive overview of the implementation progress for the Project Discovery Tool, an automated web-scraping, classification, and interactive dashboard system. It details what was accomplished across Phase 1 through Phase 4 to align all team members on system architecture, database design, backend API endpoints, automated scraping workflows, frontend dashboard UI, and team deployment setup.

## Technical Stack Overview

| Layer | Technology / Tool | Primary Function |
| --- | --- | --- |
| Backend Framework | Python FastAPI | RESTful API endpoints, routing, |
|   |   | and request validation |
|   |   | Relational storage, user |
| Database & Auth | Supabase / PostgreSQL | management, and data |
|   |   | persistence |
| Frontend Framework | React.js & CSS3 | Dark-mode interactive user |
|   |   | interface and visual dashboards |
| Data Pipeline | BeautifulSoup4 & Requests | Automated web scraping, HTML |
|   |   | parsing, and data ingestion |
| Version Control | GitHub (WebScraping repo) | Codebase management, issue |
|   |   | tracking, and team collaboration |

## Detailed Phase Breakdown

## Phase 1: Architecture & Requirements Definition

Objective: Establish core project goals, system architecture, data flow schemas, and technology stack selection.

- System Objectives: Configured the platform to automatically monitor permitted web sources, extract structured project posts, classify relevance via defined keywords/rules,


deduplicate ingested data, store clean entries in PostgreSQL, and present results on an interactive dashboard.

- Environment Setup: Configured local development environment and directory structure cleanly separated into backend/ and frontend/ services.

- Schema Blueprinting: Designed the foundational database table schema to accommodate projects, source links, dynamic status flags, and classification tags.

## Phase 2: Schema Design & Supabase Integration

Objective: Build resilient relational database models and establish backend-to-database communication.

- Database Construction: Created PostgreSQL tables in Supabase with structured attributes including primary keys, post titles, detailed descriptions, source URLs, timestamps, and categorization tags.

- Validation Models: Defined Pydantic schemas (schemas.py) within FastAPI for strict input validation, data sanitization, and response modeling.

- Security & Environment Configuration: Configured secure environment variables (.env) for storing sensitive Supabase API keys, connection strings, and database secrets.

## Phase 3: Core API Endpoints & CRUD Operations

Objective: Implement functional FastAPI RESTful endpoints for complete operational control.

- GET /projects: Fetches all scraped project entries from Supabase with support for live query search and keyword filtering.

- POST /projects: Supports manual creation or programmatic insertion of new project entries into the database.

- DELETE /projects/{id}: Enables direct removal of irrelevant, duplicate, or outdated entries straight from the management dashboard.

- Interactive Testing: Verified and validated all REST endpoints using FastAPI's automatically generated Swagger UI documentation interface.

## Phase 4: Automated Scraping Pipeline & Dashboard Interface

Objective: Automate data ingestion workflows and construct the user-facing interface.

- Automated Scraper (scraper.py): Developed a BeautifulSoup parser to scan source web pages, pull project listings, clean and deduplicate raw content, and automatically insert processed records into Supabase.

- React Web Interface (App.js, App.css): Built a dark-mode interactive web dashboard featuring live dynamic search/filtering, quick deletion actions, and direct redirection links to source project posts.


- Integration Verification: Executed comprehensive end-to-end integration tests confirming seamless data flow across the local scraper, FastAPI layer, Supabase database, and React UI.

## Current Status & Next Steps (Phase 5 Collaboration)

- 1. Repository Setup: GitHub repository is organized into clean backend/ and frontend/ directories for parallel development.

- 2. Team Onboarding: Teammates have been granted repository and workspace access via GitHub Collaborators and Supabase Team Settings.

- 3. Immediate Onboarding Tasks for Team Members:

- Clone the central repository locally.

- Configure your local .env variables using the shared Supabase project credentials.

- Install backend and frontend dependencies:

- Backend: pip install -r requirements.txt

- Frontend: npm install

- Spin up local development servers:

- Backend API: uvicorn main:app --reload

- Frontend Interface: npm start
