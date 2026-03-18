"""
skin_analyzer.py — CNN-based skin type classification via OpenAI Vision
MSc Thesis Prototype

Uses GPT-4o-mini's vision capability to analyse a face photo and classify
skin type. No separate model hosting required — reuses the existing
OPENAI_API_KEY already configured in the app.

Returns one of: oily | dry | combination | sensitive
"""

import os
import io
import base64
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

SKIN_TYPES_VALID = {"oily", "dry", "combination", "sensitive"}

ANALYSIS_PROMPT = """You are a dermatology assistant specialising in skin analysis across all skin tones.

Analyse this face photo and classify the person's skin type. You MUST always return one of the four skin types — never return null unless the image contains no face at all (e.g. a blank image or object).

Respond with ONLY a JSON object in this exact format, nothing else:
{
  "skin_type": "oily" | "dry" | "combination" | "sensitive",
  "confidence": 0.0 to 1.0,
  "reasoning": "one sentence explanation",
  "signs_observed": ["sign1", "sign2"]
}

Classification guide (applies to ALL skin tones including dark/deep skin):
- oily: shine or sheen on forehead, nose or chin; pores appear enlarged; skin looks smooth and plump; common in darker skin tones which naturally produce more sebum
- dry: skin appears matte or ashy; surface looks uneven or tight; may show texture or fine dry lines; ashiness is the dry-skin signal in deeper skin tones
- combination: mixed signals — some areas (T-zone) look shinier or smoother while cheeks look more matte or textured
- sensitive: visible unevenness, blotchiness, or post-inflammatory marks; reactive appearance

When uncertain between two types, pick the most likely one and set confidence between 0.4 and 0.6. Never return null for a clear face photo.
"""


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 JPEG string."""
    buf = io.BytesIO()
    image.convert("RGB").resize((512, 512), Image.LANCZOS).save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def classify_skin_type(image: Image.Image) -> dict:
    """
    Classify skin type from a PIL Image using GPT-4o-mini vision.

    Returns:
        {
            "skin_type":      str | None,
            "confidence":     float,
            "raw_scores":     dict,   # signs observed mapped to display
            "reasoning":      str,
            "error":          str | None,
        }
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {
            "skin_type": None, "confidence": 0.0, "raw_scores": {},
            "reasoning": "", "error": "OPENAI_API_KEY not set.",
        }

    import json
    import requests

    b64_image = _image_to_base64(image)

    payload = {
        "model": "gpt-4o-mini",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
    }

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            return {
                "skin_type": None, "confidence": 0.0, "raw_scores": {},
                "reasoning": "", "error": f"OpenAI API error {resp.status_code}.",
            }

        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        result = json.loads(content)

        skin_type  = result.get("skin_type")
        confidence = float(result.get("confidence", 0.0))
        reasoning  = result.get("reasoning", "")
        signs      = result.get("signs_observed", [])

        # If model returned null despite a clear photo, default to combination
        # (statistically the most common skin type) with low confidence
        if skin_type not in SKIN_TYPES_VALID:
            skin_type  = "combination"
            confidence = 0.4
            reasoning  = reasoning or "Could not determine definitively — defaulting to combination as the most common skin type. Please review and adjust manually."

        # Build raw_scores from signs for display
        raw_scores = {sign: 1.0 for sign in signs}

        return {
            "skin_type":  skin_type,
            "confidence": round(confidence, 3),
            "raw_scores": raw_scores,
            "reasoning":  reasoning,
            "error":      None,
        }

    except json.JSONDecodeError:
        return {
            "skin_type": None, "confidence": 0.0, "raw_scores": {},
            "reasoning": "", "error": "Could not parse model response. Please try again.",
        }
    except requests.exceptions.Timeout:
        return {
            "skin_type": None, "confidence": 0.0, "raw_scores": {},
            "reasoning": "", "error": "Request timed out. Please try again.",
        }
    except Exception as exc:
        return {
            "skin_type": None, "confidence": 0.0, "raw_scores": {},
            "reasoning": "", "error": f"Analysis failed: {str(exc)}",
        }


def get_skin_analysis_tips() -> list[str]:
    return [
        "Use a clear, well-lit photo — natural daylight works best",
        "Face the camera directly with no heavy makeup",
        "Ensure your full face is visible and in focus",
        "Avoid filters, heavy shadows, or sunglasses",
    ]