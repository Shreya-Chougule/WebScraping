-- ============================================================
-- Migration 05: Persistent Recurring Scraping Schedules
-- ScrapeScout – Web & App Project Discovery Tool
-- ============================================================
-- Note: Do NOT execute this migration automatically against the
-- production Supabase database without review and approval.
-- Apply via the Supabase SQL Editor when ready.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.scraping_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES public.sources(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'custom')),
    time_of_day TEXT NOT NULL DEFAULT '09:00',
    weekdays INTEGER[] DEFAULT NULL,
    day_of_month INTEGER DEFAULT NULL CHECK (
        day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)
    ),
    cron_expression TEXT DEFAULT NULL,
    interval_minutes INTEGER DEFAULT NULL CHECK (
        interval_minutes IS NULL OR interval_minutes >= 1
    ),
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    max_pages INTEGER NOT NULL DEFAULT 3 CHECK (max_pages >= 1 AND max_pages <= 20),
    min_request_interval DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (min_request_interval >= 0),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ DEFAULT NULL,
    last_run_status TEXT DEFAULT NULL CHECK (
        last_run_status IS NULL OR last_run_status IN ('RUNNING', 'SUCCESS', 'FAILED')
    ),
    last_error TEXT DEFAULT NULL,
    next_run_at TIMESTAMPTZ DEFAULT NULL,
    created_by UUID DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_scraping_schedules_source_id
    ON public.scraping_schedules(source_id);

CREATE INDEX IF NOT EXISTS idx_scraping_schedules_enabled
    ON public.scraping_schedules(is_enabled);

CREATE INDEX IF NOT EXISTS idx_scraping_schedules_next_run_at
    ON public.scraping_schedules(next_run_at);

ALTER TABLE public.scraping_schedules ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.scraping_schedules FROM PUBLIC, anon, authenticated;
GRANT ALL ON TABLE public.scraping_schedules TO service_role;

-- ============================================================
-- Reversible Rollback (Run only if reverting Migration 05)
-- ============================================================
-- DROP TABLE IF EXISTS public.scraping_schedules;
