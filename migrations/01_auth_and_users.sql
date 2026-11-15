
-- Migration 01: Authentication, Users & Role-Based Access Control
-- Apply only after reviewing and approving this migration.

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin', 'viewer')),
    full_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON public.users(email);

CREATE INDEX IF NOT EXISTS idx_users_role
    ON public.users(role);

-- Enable RLS.
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Remove policies from the previous migration.
DROP POLICY IF EXISTS "Users can view own profile"
    ON public.users;

DROP POLICY IF EXISTS "Admins can view all profiles"
    ON public.users;

DROP POLICY IF EXISTS "Users can update own profile"
    ON public.users;

DROP POLICY IF EXISTS "Admins can update all user profiles"
    ON public.users;

-- Users can read only their own profile.
-- Admin listing is performed through the trusted backend service role.
CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = id);

-- Prevent direct profile creation, modification, and deletion
-- by anon/authenticated clients. Backend service-role operations
-- remain available.
REVOKE ALL ON TABLE public.users FROM PUBLIC, anon, authenticated;

GRANT SELECT ON TABLE public.users TO authenticated;
GRANT ALL ON TABLE public.users TO service_role;

-- Remove the old role protection trigger and function.
DROP TRIGGER IF EXISTS trg_protect_user_role ON public.users;

DROP FUNCTION IF EXISTS public.protect_user_role();

-- New Supabase Auth users are always created as viewers.
-- User-supplied metadata cannot grant administrator privileges.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.users (
        id,
        email,
        full_name,
        role
    )
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', ''),
        'viewer'
    )
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
