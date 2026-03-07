-- ============================================================
-- migrate_to_real_products.sql
-- MSc Thesis Prototype
--
-- Table columns match the CSV headers EXACTLY so Supabase's
-- built-in CSV importer works with zero mapping.
--
-- CSV columns (in order):
--   product_id, product_name, brand_id, brand_name,
--   loves_count, rating, reviews, size,
--   variation_type, variation_value, variation_desc,
--   ingredients, price_usd, value_price_usd, sale_price_usd,
--   limited_edition, new, online_only, out_of_stock, sephora_exclusive,
--   highlights, primary_category, secondary_category, tertiary_category,
--   child_count, child_max_price, child_min_price
-- ============================================================


-- ────────────────────────────────────────────
-- 1. Drop old objects
-- ────────────────────────────────────────────
DROP VIEW  IF EXISTS product_collab_scores;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS products  CASCADE;


-- ────────────────────────────────────────────
-- 2. Products table — columns match CSV exactly
-- ────────────────────────────────────────────
CREATE TABLE products (
    product_id          TEXT            PRIMARY KEY,
    product_name        TEXT,
    brand_id            INTEGER,
    brand_name          TEXT,
    loves_count         INTEGER,
    rating              NUMERIC(7,4),
    reviews             INTEGER,
    size                TEXT,
    variation_type      TEXT,
    variation_value     TEXT,
    variation_desc      TEXT,
    ingredients         TEXT,
    price_usd           NUMERIC(10,2),
    value_price_usd     NUMERIC(10,2),
    sale_price_usd      NUMERIC(10,2),
    limited_edition     SMALLINT,       -- 0 or 1 (matches CSV integers)
    "new"               SMALLINT,       -- quoted because NEW is a SQL keyword
    online_only         SMALLINT,
    out_of_stock        SMALLINT,
    sephora_exclusive   SMALLINT,
    highlights          TEXT,           -- stored as Python-style list string from CSV
    primary_category    TEXT,
    secondary_category  TEXT,
    tertiary_category   TEXT,
    child_count         INTEGER,
    child_max_price     NUMERIC(10,2),
    child_min_price     NUMERIC(10,2)
);


-- ────────────────────────────────────────────
-- 3. Indexes
-- ────────────────────────────────────────────
CREATE INDEX idx_products_primary_cat ON products (primary_category);
CREATE INDEX idx_products_brand       ON products (brand_name);
CREATE INDEX idx_products_rating      ON products (rating DESC NULLS LAST);
CREATE INDEX idx_products_price       ON products (price_usd NULLS LAST);


-- ────────────────────────────────────────────
-- 4. Row Level Security
-- ────────────────────────────────────────────
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read products"
    ON products FOR SELECT
    USING (true);


-- ────────────────────────────────────────────
-- 5. Feedback table (product_id is TEXT FK)
-- ────────────────────────────────────────────
CREATE TABLE feedback (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID,
    product_id  TEXT         NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    rating      SMALLINT     CHECK (rating >= 1 AND rating <= 5),
    created_at  TIMESTAMPTZ  DEFAULT now()
);

ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages feedback"
    ON feedback FOR ALL
    USING (true);


-- ────────────────────────────────────────────
-- 6. Collaborative filtering view
-- ────────────────────────────────────────────
CREATE OR REPLACE VIEW product_collab_scores AS
SELECT
    product_id,
    AVG(rating)::NUMERIC(4,4)  AS avg_user_rating,
    COUNT(*)                   AS feedback_count
FROM feedback
GROUP BY product_id;


-- ────────────────────────────────────────────
-- 7. Recommendation history (unchanged)
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendation_history (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID         NOT NULL,
    profile     TEXT,
    products    TEXT,
    created_at  TIMESTAMPTZ  DEFAULT now()
);

ALTER TABLE recommendation_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages history"
    ON recommendation_history FOR ALL
    USING (true);
