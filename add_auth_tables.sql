-- ============================================================
-- add_auth_tables.sql
-- Run this in Supabase SQL Editor AFTER setup.sql
--
-- Adds the recommendation_history table and updates RLS
-- policies so users can only read their own history.
-- ============================================================


-- ────────────────────────────────────────────
-- TABLE: recommendation_history
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.recommendation_history (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL,           -- matches auth.users.id
    profile     TEXT        NOT NULL,           -- JSON: skin profile used for this query
    products    TEXT        NOT NULL,           -- JSON: snapshot of top-N products returned
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ────────────────────────────────────────────
-- Row Level Security
-- ────────────────────────────────────────────

ALTER TABLE public.recommendation_history ENABLE ROW LEVEL SECURITY;

-- Users can insert their own history rows
CREATE POLICY "Users can insert own history"
    ON public.recommendation_history
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can only read their own history rows
CREATE POLICY "Users can read own history"
    ON public.recommendation_history
    FOR SELECT
    USING (auth.uid() = user_id);


-- ────────────────────────────────────────────
-- Also update feedback RLS to link feedback to auth users (optional improvement)
-- ────────────────────────────────────────────

-- Add an optional user_id column to feedback so history is traceable
ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS user_id UUID;


-- ────────────────────────────────────────────
-- Verify
-- ────────────────────────────────────────────

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
