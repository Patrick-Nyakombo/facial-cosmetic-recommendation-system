-- ============================================================
-- add_user_profiles_and_reviews.sql
-- MSc Thesis Prototype
--
-- Run this AFTER migrate_to_real_products.sql
--
-- Adds:
--   1. user_profiles table  — stores skin type, concerns, display name
--   2. Extends feedback table — adds review_text, is_recommended
--   3. Recreates product_collab_scores view with helpfulness weighting
--   4. admin_users table     — simple email-based admin role list
-- ============================================================


-- ────────────────────────────────────────────
-- 1. User profiles
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         UUID        PRIMARY KEY,   -- matches Supabase auth.users.id
    display_name    TEXT,
    skin_type       TEXT,                      -- oily | dry | combination | sensitive
    skin_concerns   TEXT,                      -- JSON array: ["acne","aging",...]
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages profiles"
    ON user_profiles FOR ALL
    USING (true);


-- ────────────────────────────────────────────
-- 2. Extend feedback with review fields
-- ────────────────────────────────────────────
ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS is_recommended  BOOLEAN,
    ADD COLUMN IF NOT EXISTS review_text     TEXT,
    ADD COLUMN IF NOT EXISTS helpfulness     NUMERIC(6,4) DEFAULT 0;


-- ────────────────────────────────────────────
-- 3. Rebuild collab view — helpfulness-weighted average
--    weighted_rating = rating * (1 + helpfulness)
--    This rewards reviews users found helpful
-- ────────────────────────────────────────────
CREATE OR REPLACE VIEW product_collab_scores AS
SELECT
    product_id,
    SUM(rating * (1.0 + COALESCE(helpfulness, 0)))
        / NULLIF(SUM(1.0 + COALESCE(helpfulness, 0)), 0)  AS avg_user_rating,
    COUNT(*)                                               AS feedback_count,
    AVG(CASE WHEN is_recommended THEN 1.0 ELSE 0.0 END)   AS recommend_rate
FROM feedback
GROUP BY product_id;


-- ────────────────────────────────────────────
-- 4. Admin users table
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
    email       TEXT    PRIMARY KEY,
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages admins"
    ON admin_users FOR ALL
    USING (true);

-- Add your admin email here:
-- INSERT INTO admin_users (email) VALUES ('your@email.com');
