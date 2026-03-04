"""
openai_service.py - OpenAI API Integration Layer
MSc Thesis Prototype

Responsibilities:
  - Build structured prompts for product explanation
  - Call OpenAI Chat Completion API
  - Handle errors gracefully so UI never crashes
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env so the module works when imported directly
load_dotenv()

# ─────────────────────────────────────────────
# OpenAI client (lazy-initialised)
# ─────────────────────────────────────────────

def _get_client() -> OpenAI:
    """Return an authenticated OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Missing OPENAI_API_KEY environment variable. "
            "Please add it to your .env file."
        )
    return OpenAI(api_key=api_key)


# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────

def _build_prompt(
    product_name: str,
    skin_type: str,
    concern: str,
    ingredients: str,
    rating: float,
) -> str:
    """
    Construct the user-facing explanation prompt.

    The prompt is designed to yield concise, factual 3-sentence responses
    suitable for a thesis demonstration.

    Args:
        product_name: Name of the cosmetic product.
        skin_type:    User's declared skin type.
        concern:      User's primary skin concern.
        ingredients:  Product ingredient list (raw string from DB).
        rating:       Numeric product rating (0–5).

    Returns:
        Formatted prompt string.
    """
    return (
        f"Explain in 3 concise sentences why the cosmetic product '{product_name}' "
        f"is suitable for a user with the following profile:\n"
        f"- Skin type: {skin_type}\n"
        f"- Skin concern: {concern}\n"
        f"- Key ingredients: {ingredients}\n"
        f"- Product rating: {rating}/5\n\n"
        f"Focus on the relationship between the ingredients and the user's skin profile."
    )


# ─────────────────────────────────────────────
# Main explanation function
# ─────────────────────────────────────────────

def generate_explanation(
    product_name: str,
    skin_type: str,
    concern: str,
    ingredients: str,
    rating: float,
) -> str | None:
    """
    Generate a personalised product explanation via OpenAI Chat API.

    Args:
        product_name: Name of the cosmetic product.
        skin_type:    User's declared skin type.
        concern:      User's primary skin concern.
        ingredients:  Ingredient list string from the database.
        rating:       Product rating (0–5).

    Returns:
        Explanation string, or None if the API call fails.
    """
    try:
        client = _get_client()

        prompt = _build_prompt(
            product_name=product_name,
            skin_type=skin_type,
            concern=concern,
            ingredients=ingredients,
            rating=rating,
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",          # Cost-effective model; swap to gpt-4o if needed
            temperature=0.3,              # Low temperature for factual, consistent output
            max_tokens=150,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional cosmetic dermatologist assistant. "
                        "Provide evidence-based, concise product explanations tailored "
                        "to a user's specific skin type and concern."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        # Extract the text content from the first choice
        return response.choices[0].message.content.strip()

    except EnvironmentError as env_err:
        # Missing API key — surface clearly
        print(f"[openai_service] Configuration error: {env_err}")
        return None

    except Exception as exc:
        # Any other OpenAI or network error — log but don't crash the app
        print(f"[openai_service] OpenAI API error: {exc}")
        return None
