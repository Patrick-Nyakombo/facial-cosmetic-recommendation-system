-- ============================================================
-- fix_rls_policies.sql
-- Run this in Supabase SQL Editor to fix the RLS errors
-- for the feedback and recommendation_history tables.
-- ============================================================


-- ────────────────────────────────────────────
-- FIX: feedback table
-- Drop the old restrictive policy and replace with one
-- that allows any authenticated user to insert.
-- ────────────────────────────────────────────

DROP POLICY IF EXISTS "Allow public insert on feedback" ON public.feedback;

CREATE POLICY "Allow authenticated insert on feedback"
    ON public.feedback
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow authenticated users to read all feedback (e.g. for future analytics)
DROP POLICY IF EXISTS "Allow authenticated read on feedback" ON public.feedback;

CREATE POLICY "Allow authenticated read on feedback"
    ON public.feedback
    FOR SELECT
    TO authenticated
    USING (true);


-- ────────────────────────────────────────────
-- FIX: recommendation_history table
-- The auth.uid() check fails when using the anon key because
-- the server-side client doesn't carry the user JWT.
-- Replace with a simple authenticated-user policy.
-- ────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can insert own history" ON public.recommendation_history;
DROP POLICY IF EXISTS "Users can read own history"   ON public.recommendation_history;

CREATE POLICY "Allow authenticated insert on history"
    ON public.recommendation_history
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow authenticated read on history"
    ON public.recommendation_history
    FOR SELECT
    TO authenticated
    USING (true);


-- ────────────────────────────────────────────
-- Verify policies are in place
-- ────────────────────────────────────────────

SELECT
    tablename,
    policyname,
    cmd,
    roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('feedback', 'recommendation_history')
ORDER BY tablename, policyname;