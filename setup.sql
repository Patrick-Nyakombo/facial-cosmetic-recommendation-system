-- ============================================================
-- Facial Cosmetics Recommendation System — Supabase SQL Setup
-- MSc Thesis Prototype
--
-- HOW TO RUN:
--   1. Go to your Supabase project dashboard
--   2. Click "SQL Editor" in the left sidebar
--   3. Paste this entire file and click "Run"
-- ============================================================


-- ────────────────────────────────────────────
-- TABLE: products
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.products (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    brand       TEXT        NOT NULL,
    price       NUMERIC     NOT NULL CHECK (price >= 0),
    skin_type   TEXT        NOT NULL CHECK (skin_type IN ('oily', 'dry', 'combination', 'sensitive')),
    concern     TEXT        NOT NULL CHECK (concern IN ('acne', 'aging', 'hyperpigmentation', 'dryness')),
    ingredients TEXT        NOT NULL,
    rating      NUMERIC     NOT NULL CHECK (rating >= 0 AND rating <= 5)
);


-- ────────────────────────────────────────────
-- TABLE: feedback
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.feedback (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID        NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    rating      NUMERIC     NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ────────────────────────────────────────────
-- SAMPLE DATA: products
-- 20 products covering all skin_type × concern combinations
-- ────────────────────────────────────────────

INSERT INTO public.products (name, brand, price, skin_type, concern, ingredients, rating) VALUES

-- OILY + ACNE
('ClearSkin Foaming Gel',       'PureDerm',      18.99, 'oily', 'acne',             'water, salicylic acid, niacinamide, zinc PCA, glycerin, aloe vera',                         4.5),
('BlemishFix Serum',            'AcneClear',     24.50, 'oily', 'acne',             'water, benzoyl peroxide, tea tree oil, hyaluronic acid, panthenol',                         4.2),
('Oil Control Mattifier',       'DermPure',      15.00, 'oily', 'acne',             'water, niacinamide, salicylic acid, kaolin clay, witch hazel, glycerin',                     3.9),

-- OILY + AGING
('Youth Renewal Oil Serum',     'AgelessGlow',   39.99, 'oily', 'aging',            'water, retinol, niacinamide, hyaluronic acid, vitamin C, jojoba oil',                       4.6),
('Firming Day Fluid',           'SkinScience',   32.00, 'oily', 'aging',            'water, peptides, retinol, glycerin, green tea extract, vitamin E',                          4.1),

-- OILY + HYPERPIGMENTATION
('BrightEven Tone Serum',       'LumiSkin',      29.99, 'oily', 'hyperpigmentation','water, vitamin C, kojic acid, niacinamide, alpha arbutin, hyaluronic acid',                 4.7),
('Dark Spot Corrector Gel',     'ClearTone',     22.00, 'oily', 'hyperpigmentation','water, alpha arbutin, tranexamic acid, niacinamide, glycerin, aloe vera',                   4.3),

-- OILY + DRYNESS
('Lightweight Hydra Gel',       'AquaBalance',   19.50, 'oily', 'dryness',          'water, hyaluronic acid, glycerin, aloe vera, green tea extract, panthenol',                 4.4),
('Oil-Free Moisture Surge',     'HydraLab',      21.00, 'oily', 'dryness',          'water, hyaluronic acid, niacinamide, glycerin, cucumber extract, allantoin',                4.0),

-- DRY + ACNE
('Gentle Acne Cream',           'SoftClear',     27.00, 'dry',  'acne',             'water, salicylic acid, ceramides, shea butter, glycerin, panthenol',                        4.2),
('Soothing Blemish Balm',       'KindSkin',      23.50, 'dry',  'acne',             'water, benzoyl peroxide, ceramides, squalane, aloe vera, allantoin',                        3.8),

-- DRY + AGING
('Rich Renewal Cream',          'VelvetAge',     44.99, 'dry',  'aging',            'water, retinol, shea butter, ceramides, hyaluronic acid, peptides, vitamin E',              4.8),
('Deep Lift Moisturiser',       'PrimaDerm',     38.00, 'dry',  'aging',            'water, peptides, squalane, shea butter, retinol, rosehip oil, glycerin',                    4.5),

-- DRY + HYPERPIGMENTATION
('Radiance Repair Cream',       'GlowRich',      34.00, 'dry',  'hyperpigmentation','water, vitamin C, niacinamide, shea butter, alpha arbutin, ceramides, glycerin',            4.6),

-- DRY + DRYNESS
('Intense Moisture Barrier',    'OceanDerm',     29.00, 'dry',  'dryness',          'water, ceramides, shea butter, squalane, hyaluronic acid, glycerin, panthenol',             4.9),

-- COMBINATION + ACNE
('Balancing Acne Gel',          'EquiSkin',      20.00, 'combination', 'acne',      'water, salicylic acid, niacinamide, zinc PCA, hyaluronic acid, aloe vera',                  4.3),

-- COMBINATION + AGING
('Dual-Zone Anti-Age Fluid',    'FlexDerm',      36.00, 'combination', 'aging',     'water, retinol, hyaluronic acid, peptides, niacinamide, vitamin C, glycerin',               4.4),

-- SENSITIVE + ACNE
('Calm & Clear Lotion',         'GentleRx',      25.00, 'sensitive', 'acne',        'water, salicylic acid, centella asiatica, ceramides, glycerin, allantoin',                  4.1),

-- SENSITIVE + AGING
('Soothing Firm Serum',         'SilkAge',       41.00, 'sensitive', 'aging',       'water, peptides, centella asiatica, hyaluronic acid, ceramides, panthenol',                 4.5),

-- SENSITIVE + HYPERPIGMENTATION
('Calming Bright Essence',      'TranquilGlow',  31.00, 'sensitive', 'hyperpigmentation','water, tranexamic acid, centella asiatica, niacinamide, glycerin, allantoin, aloe vera', 4.3);


-- ────────────────────────────────────────────
-- Enable Row Level Security (optional but recommended)
-- ────────────────────────────────────────────

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback  ENABLE ROW LEVEL SECURITY;

-- Allow anonymous reads on products (needed for the app's anon key)
CREATE POLICY "Allow public read on products"
    ON public.products FOR SELECT
    USING (true);

-- Allow anonymous inserts on feedback
CREATE POLICY "Allow public insert on feedback"
    ON public.feedback FOR INSERT
    WITH CHECK (true);


-- ────────────────────────────────────────────
-- Verify: quick row counts
-- ────────────────────────────────────────────

SELECT
    'products' AS table_name, COUNT(*) AS row_count FROM public.products
UNION ALL
SELECT
    'feedback', COUNT(*) FROM public.feedback;
