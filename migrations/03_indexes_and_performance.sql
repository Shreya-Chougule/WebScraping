-- ============================================================
-- Migration 03: Database Query Optimization & Index Recommendations
-- ScrapeScout – Web & App Project Discovery Tool
-- ============================================================
-- Note: Do NOT execute this migration automatically against the
-- production Supabase database. Apply via the Supabase SQL Editor
-- when deployment is approved.
-- ============================================================

-- 1. Index on project posted_date for date-range queries & search
CREATE INDEX IF NOT EXISTS idx_projects_posted_date ON public.projects(posted_date DESC);

-- 2. Index on project created_at for daily opportunity compilation
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON public.projects(created_at DESC);

-- 3. Index on project_type for fast categorical filtering (Web, App, Software, Both)
CREATE INDEX IF NOT EXISTS idx_projects_project_type ON public.projects(project_type);

-- 4. Index on category for classification-based filtering
CREATE INDEX IF NOT EXISTS idx_projects_category ON public.projects(category);

-- 5. Index on source_id for filtering opportunities by platform
CREATE INDEX IF NOT EXISTS idx_projects_source_id ON public.projects(source_id);

-- 6. Partial index on non-duplicate records for daily opportunity queries
CREATE INDEX IF NOT EXISTS idx_projects_non_duplicates ON public.projects(is_duplicate)
WHERE is_duplicate IS FALSE OR is_duplicate IS NULL;

-- 7. GIN index for full-text search across title and description
CREATE INDEX IF NOT EXISTS idx_projects_text_search ON public.projects
USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- 8. GIN index on required_technologies JSON array
CREATE INDEX IF NOT EXISTS idx_projects_technologies ON public.projects
USING gin(required_technologies);

