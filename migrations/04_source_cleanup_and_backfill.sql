-- ============================================================
-- Migration 04: Safe Source Cleanup & Truelancer source_id Backfill
-- ScrapeScout – Web & App Project Discovery Tool
-- ============================================================
-- Note: Do NOT execute this migration automatically against the
-- production Supabase database without review and approval.
-- Apply via the Supabase SQL Editor when ready.
-- ============================================================

-- 1. Mark non-integrated / placeholder sources inactive (reversible, non-destructive)
-- Keeps Truelancer active while hiding unintegrated or sample sources
-- such as "Sample Job Board" and "LinkedIn Industry Hub" from active analytics.
UPDATE public.sources
SET is_active = FALSE
WHERE LOWER(TRIM(name)) <> 'truelancer'
  AND is_active IS TRUE;

-- 2. Safely backfill NULL source_id values for genuine Truelancer projects only.
-- Matches strictly on Truelancer URLs and links them to the active Truelancer source.
WITH active_truelancer AS (
    SELECT id
    FROM public.sources
    WHERE LOWER(TRIM(name)) = 'truelancer'
      AND is_active IS TRUE
    ORDER BY created_at ASC
    LIMIT 1
)
UPDATE public.projects AS p
SET source_id = active_truelancer.id
FROM active_truelancer
WHERE p.source_id IS NULL
  AND p.original_url ~* '^https?://([a-z0-9-]+\.)?truelancer\.com(/|$)';
