-- ============================================================
-- add_category_and_collab.sql
-- Run in Supabase SQL Editor
--
-- 1. Adds `category` column to products
-- 2. Updates all existing products with their category
-- 3. Inserts new products to cover more categories
-- 4. Creates user_item_ratings view for collaborative filtering
-- ============================================================


-- ────────────────────────────────────────────
-- Step 1: Add category column
-- ────────────────────────────────────────────

ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'moisturizer';

ALTER TABLE public.products
    ADD CONSTRAINT products_category_check
    CHECK (category IN (
        'moisturizer', 'serum', 'cleanser', 'lip', 'eye cream',
        'sunscreen', 'toner', 'mask', 'foundation', 'blush'
    ));

-- Also add user_id to feedback if not already there
ALTER TABLE public.feedback
    ADD COLUMN IF NOT EXISTS user_id UUID;


-- ────────────────────────────────────────────
-- Step 2: Update existing products with categories
-- ────────────────────────────────────────────

UPDATE public.products SET category = 'cleanser'    WHERE name = 'ClearSkin Foaming Gel';
UPDATE public.products SET category = 'serum'       WHERE name = 'BlemishFix Serum';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Oil Control Mattifier';
UPDATE public.products SET category = 'serum'       WHERE name = 'Youth Renewal Oil Serum';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Firming Day Fluid';
UPDATE public.products SET category = 'serum'       WHERE name = 'BrightEven Tone Serum';
UPDATE public.products SET category = 'serum'       WHERE name = 'Dark Spot Corrector Gel';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Lightweight Hydra Gel';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Oil-Free Moisture Surge';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Gentle Acne Cream';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Soothing Blemish Balm';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Rich Renewal Cream';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Deep Lift Moisturiser';
UPDATE public.products SET category = 'serum'       WHERE name = 'Radiance Repair Cream';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Intense Moisture Barrier';
UPDATE public.products SET category = 'cleanser'    WHERE name = 'Balancing Acne Gel';
UPDATE public.products SET category = 'serum'       WHERE name = 'Dual-Zone Anti-Age Fluid';
UPDATE public.products SET category = 'moisturizer' WHERE name = 'Calm & Clear Lotion';
UPDATE public.products SET category = 'serum'       WHERE name = 'Soothing Firm Serum';
UPDATE public.products SET category = 'serum'       WHERE name = 'Calming Bright Essence';


-- ────────────────────────────────────────────
-- Step 3: Insert new products covering more categories
-- ────────────────────────────────────────────

INSERT INTO public.products (name, brand, price, skin_type, concern, ingredients, rating, category) VALUES

-- LIP PRODUCTS
('Hydra Lip Balm SPF 15',       'LipLux',     12.99, 'dry',         'dryness',          'water, shea butter, vitamin E, beeswax, hyaluronic acid, SPF 15',               4.6, 'lip'),
('Plump & Glow Lip Serum',      'GlossRx',    19.50, 'sensitive',   'dryness',          'water, hyaluronic acid, peptides, centella asiatica, vitamin C, glycerin',       4.4, 'lip'),
('Mattifying Lip Primer',       'MatteLab',   14.00, 'oily',        'acne',             'water, niacinamide, salicylic acid, zinc oxide, dimethicone',                    3.9, 'lip'),
('Anti-Age Lip Treatment',      'VelvetAge',  24.00, 'dry',         'aging',            'water, retinol, peptides, shea butter, ceramides, vitamin E',                   4.7, 'lip'),
('Brightening Lip Mask',        'LumiSkin',   16.00, 'combination', 'hyperpigmentation','water, vitamin C, kojic acid, hyaluronic acid, honey extract, glycerin',         4.3, 'lip'),

-- EYE CREAM
('Depuff Eye Gel',              'AquaBalance', 28.00, 'oily',       'aging',            'water, caffeine, hyaluronic acid, niacinamide, green tea extract, peptides',     4.5, 'eye cream'),
('Brightening Eye Serum',       'LumiSkin',   35.00, 'dry',        'hyperpigmentation','water, vitamin C, alpha arbutin, peptides, ceramides, squalane',                  4.6, 'eye cream'),
('Calming Eye Balm',            'GentleRx',   22.00, 'sensitive',  'dryness',          'water, centella asiatica, ceramides, shea butter, allantoin, chamomile',          4.4, 'eye cream'),
('Firming Eye Cream',           'PrimaDerm',  42.00, 'combination','aging',            'water, retinol, peptides, hyaluronic acid, niacinamide, vitamin E',               4.8, 'eye cream'),

-- TONER
('Balancing Toner Mist',        'EquiSkin',   18.00, 'combination','acne',             'water, niacinamide, witch hazel, salicylic acid, aloe vera, glycerin',            4.2, 'toner'),
('Hydrating Rose Toner',        'OceanDerm',  21.00, 'dry',        'dryness',          'water, rose water, hyaluronic acid, glycerin, ceramides, allantoin',              4.7, 'toner'),
('Brightening Toner',           'ClearTone',  19.00, 'oily',       'hyperpigmentation','water, vitamin C, niacinamide, AHA, witch hazel, aloe vera',                      4.3, 'toner'),
('Soothing Centella Toner',     'KindSkin',   17.00, 'sensitive',  'acne',             'water, centella asiatica, ceramides, allantoin, glycerin, panthenol',             4.5, 'toner'),

-- SUNSCREEN
('Daily UV Fluid SPF 50',       'SkinScience', 22.00,'oily',       'aging',            'water, zinc oxide, niacinamide, hyaluronic acid, vitamin E, SPF 50',              4.6, 'sunscreen'),
('Tinted Sunscreen SPF 40',     'GlowRich',   27.00, 'dry',        'hyperpigmentation','water, titanium dioxide, vitamin C, shea butter, SPF 40, ceramides',              4.5, 'sunscreen'),
('Sensitive Sun Shield SPF 30', 'GentleRx',   24.00, 'sensitive',  'dryness',          'water, zinc oxide, centella asiatica, ceramides, allantoin, SPF 30',              4.4, 'sunscreen'),
('Matte Sunscreen SPF 50+',     'DermPure',   20.00, 'combination','aging',            'water, zinc oxide, niacinamide, kaolin clay, SPF 50+, vitamin E',                 4.3, 'sunscreen'),

-- MASK
('Detox Clay Mask',             'PureDerm',   16.00, 'oily',       'acne',             'water, kaolin clay, salicylic acid, tea tree oil, niacinamide, witch hazel',      4.4, 'mask'),
('Hydrogel Sleeping Mask',      'HydraLab',   23.00, 'dry',        'dryness',          'water, hyaluronic acid, ceramides, shea butter, peptides, glycerin',               4.8, 'mask'),
('Brightening Vitamin C Mask',  'LumiSkin',   21.00, 'combination','hyperpigmentation','water, vitamin C, niacinamide, kaolin clay, kojic acid, glycerin',                4.5, 'mask'),
('Calming Oat Mask',            'KindSkin',   18.00, 'sensitive',  'dryness',          'water, oat extract, centella asiatica, ceramides, allantoin, aloe vera',          4.6, 'mask'),

-- FOUNDATION
('Skin-Tint Foundation',        'FlexDerm',   32.00, 'oily',       'acne',             'water, niacinamide, salicylic acid, SPF 20, zinc oxide, dimethicone',             4.1, 'foundation'),
('Hydrating Foundation',        'VelvetAge',  38.00, 'dry',        'aging',            'water, hyaluronic acid, ceramides, peptides, shea butter, SPF 15',                4.5, 'foundation'),
('Sensitive Skin Foundation',   'SilkAge',    35.00, 'sensitive',  'dryness',          'water, ceramides, centella asiatica, allantoin, SPF 30, glycerin',                4.3, 'foundation'),

-- BLUSH
('Cream Blush Stick',           'GlossRx',    18.00, 'dry',        'dryness',          'water, shea butter, vitamin E, jojoba oil, ceramides',                            4.4, 'blush'),
('Matte Powder Blush',          'MatteLab',   15.00, 'oily',       'acne',             'water, kaolin clay, niacinamide, zinc oxide, silica',                             4.2, 'blush'),
('Glow Blush Serum',            'LumiSkin',   22.00, 'combination','hyperpigmentation','water, vitamin C, hyaluronic acid, mica, glycerin, niacinamide',                  4.5, 'blush');


-- ────────────────────────────────────────────
-- Step 4: View for collaborative filtering
-- Aggregates average user feedback rating per product
-- ────────────────────────────────────────────

CREATE OR REPLACE VIEW public.product_collab_scores AS
SELECT
    product_id,
    AVG(rating)   AS avg_user_rating,
    COUNT(*)      AS feedback_count
FROM public.feedback
GROUP BY product_id;


-- ────────────────────────────────────────────
-- Verify
-- ────────────────────────────────────────────

SELECT category, COUNT(*) AS product_count
FROM public.products
GROUP BY category
ORDER BY category;
