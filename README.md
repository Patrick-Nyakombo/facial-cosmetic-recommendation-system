# 💄 Facial Cosmetics Recommendation System
**MSc Thesis Prototype** — Hybrid Recommender with Rule-Based Filtering, Content-Based Scoring, and OpenAI Explanations

---

## 1. Setup Instructions

### Prerequisites
- Python 3.11+
- A [Supabase](https://supabase.com) project with the `products` and `feedback` tables populated
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

### Steps

```bash
# 1. Clone / navigate to project folder
cd cosmetics-recommender

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
#    macOS/Linux:
source venv/bin/activate
#    Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure secrets
cp .env.example .env
# Then open .env and fill in OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY

# 6. Run the app
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## 2. Architecture

```
User (Streamlit UI)
        │
        ▼
  User Profile Input
  (skin type, concern, budget, avoided ingredients)
        │
        ▼
  ┌─────────────────────────┐
  │  database.py            │  Supabase → fetches all products (cached 5 min)
  └─────────────────────────┘
        │
        ▼
  ┌─────────────────────────┐
  │  recommendation_engine  │
  │  ① Rule-Based Filter    │  Hard constraints (type, concern, budget, ingredients)
  │  ② Weighted Scoring     │  Soft ranking formula
  └─────────────────────────┘
        │
        ▼
      Top-5 Products
        │
        ▼
  ┌─────────────────────────┐
  │  openai_service.py      │  GPT generates 3-sentence personalised explanation
  └─────────────────────────┘
        │
        ▼
  Streamlit Results Page
  (name, brand, price, rating, ingredients, AI explanation, feedback slider)
```

---

## 3. How the Recommendation Works

### Stage 1 — Rule-Based Filtering (Expert System)

Hard rules eliminate any product that:
- Does **not** match the user's skin type
- Does **not** target the user's skin concern
- Exceeds the user's maximum budget
- Contains any ingredient the user wants to avoid (case-insensitive match)

This mirrors a domain-expert decision tree and ensures safety and relevance.

### Stage 2 — Content-Based Weighted Scoring

Each surviving candidate receives a composite score:

```
score = 0.4 × skin_type_match
      + 0.3 × concern_match
      + 0.2 × normalised_rating
      + 0.1 × price_score
```

| Feature | Weight | Rationale |
|---|---|---|
| `skin_type_match` | 0.40 | Most critical safety factor |
| `concern_match` | 0.30 | Primary efficacy driver |
| `normalised_rating` | 0.20 | Community validation (rating / 5) |
| `price_score` | 0.10 | Value: `1 − (price / budget)` |

Products are ranked descending; the top 5 are returned.

---

## 4. How OpenAI Is Used

Each top-5 product is passed to `openai_service.generate_explanation()` which:

1. Builds a structured prompt including the product name, user's skin type, concern, product ingredients, and rating.
2. Calls `gpt-4o-mini` via the Chat Completions API with:
   - `temperature = 0.3` (factual, low variance)
   - `max_tokens = 150` (concise output)
3. A system message primes the model as a *cosmetic dermatologist assistant*.
4. The generated 3-sentence explanation is displayed in the UI below each product card.

If the OpenAI API is unavailable or the key is missing, the app degrades gracefully — it shows a warning but still displays the rule-based and scored recommendations.

---

## 5. Database Schema (Supabase)

```sql
-- products table
CREATE TABLE products (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    brand       text,
    price       numeric,
    skin_type   text,   -- 'oily' | 'dry' | 'combination' | 'sensitive'
    concern     text,   -- 'acne' | 'aging' | 'hyperpigmentation' | 'dryness'
    ingredients text,
    rating      numeric
);

-- feedback table
CREATE TABLE feedback (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  uuid REFERENCES products(id),
    rating      numeric,
    created_at  timestamptz DEFAULT now()
);
```

---

## 6. File Responsibilities

| File | Role |
|---|---|
| `app.py` | Streamlit UI: collects input, orchestrates pipeline, renders results |
| `database.py` | Supabase client, product fetching (cached), feedback insertion |
| `recommendation_engine.py` | Rule-based filter + weighted content-based scoring |
| `openai_service.py` | OpenAI Chat API call + graceful error handling |
| `requirements.txt` | Python dependencies |
| `.env.example` | Secret keys template |
