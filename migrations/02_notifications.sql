
-- ============================================================
-- Migration 02: In-App Notifications and Per-User Read Receipts
-- ScrapeScout - Web & App Project Discovery Tool
-- ============================================================
-- IMPORTANT:
-- Do NOT execute automatically against production Supabase.
-- Review and apply manually only after deployment approval.
-- ============================================================

-- 1. Notifications table
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info'
        CHECK (type IN ('info', 'success', 'warning', 'high_priority')),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    link TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);

-- 2. Per-user read receipts
CREATE TABLE IF NOT EXISTS public.notification_reads (
    notification_id UUID NOT NULL
        REFERENCES public.notifications(id) ON DELETE CASCADE,
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,
    read_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW()),

    PRIMARY KEY (notification_id, user_id)
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id
    ON public.notifications(user_id);

CREATE INDEX IF NOT EXISTS idx_notifications_created_at
    ON public.notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_reads_user_id
    ON public.notification_reads(user_id);

-- 4. Preserve existing private notification read states.
-- Old broadcast is_read values cannot safely be attributed to
-- individual users, so broadcasts start unread for each user.
INSERT INTO public.notification_reads (
    notification_id,
    user_id
)
SELECT id, user_id
FROM public.notifications
WHERE is_read = TRUE
  AND user_id IS NOT NULL
ON CONFLICT (notification_id, user_id) DO NOTHING;

-- 5. Enable RLS
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_reads ENABLE ROW LEVEL SECURITY;

-- 6. Remove old policies that permit shared broadcast updates
DROP POLICY IF EXISTS "Users can view relevant notifications"
    ON public.notifications;

DROP POLICY IF EXISTS "Users can update own notifications"
    ON public.notifications;

DROP POLICY IF EXISTS "Backend can insert notifications"
    ON public.notifications;

-- 7. Users may read their own notifications and broadcasts.
CREATE POLICY "Users can view relevant notifications"
    ON public.notifications
    FOR SELECT
    TO authenticated
    USING (
        user_id IS NULL
        OR user_id = auth.uid()
    );

-- No authenticated INSERT, UPDATE, or DELETE policy is created
-- for notifications. The backend service-role client performs
-- authorized notification creation.

-- 8. Users may read only their own read receipts.
DROP POLICY IF EXISTS "Users can view own notification reads"
    ON public.notification_reads;

CREATE POLICY "Users can view own notification reads"
    ON public.notification_reads
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- No authenticated INSERT, UPDATE, or DELETE policy is created
-- for notification_reads. The backend service-role client manages
-- read receipts after checking notification ownership.
