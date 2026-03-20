import base64
import json
import logging
import re
from typing import Optional

import anthropic

from backend.config import settings
from backend.database.queries import get_all_colors_for_prompt

logger = logging.getLogger(__name__)

CONDITION_GUIDELINES = """
Condition definitions (use visual cues):
- "new": installed within ~2 years. Granules fully intact and dense, very sharp shadow lines
  between shingle courses, colors vibrant and consistent, no granule loss visible, no fading.
- "good": normal wear, 3-15 year appearance. Some minor granule loss at edges,
  colors still reasonably vibrant, shadow lines clear but slightly softened.
- "worn": significant aging, 15+ year appearance. Visible granule loss creating bare or
  thin spots, color fading/bleaching especially on south-facing slopes, soft or blurry
  shadow lines between courses, possible minor curling at shingle edges.
- "faded": color has lightened significantly from original (often looks 2-3 shades lighter),
  but shingle structure still intact. Common on south/west exposures.
- "damaged": cracking, curling, cupping, missing sections, blistering, hail impact marks
  (round dimples), moss or algae growth (black streaks or green patches), exposed substrate.

Visual cues for condition assessment:
1. Shadow lines between shingle courses: sharp/defined = newer; soft/blurred = older
2. Granule texture: dense and uniform = newer; sparse, patchy, or chalky = worn
3. Color uniformity: consistent = newer; blotchy or gradient (darker in shadow areas) = worn/faded
4. Edge sharpness: crisp tabs = newer; rounded/frayed edges = worn
5. Reflection: slight sheen in sunlight = newer; flat/matte = older
"""

SYSTEM_PROMPT = """You are an expert roofing material identification specialist and color analyst
with 20+ years of experience identifying asphalt shingles from major manufacturers including GAF,
CertainTeed, Owens Corning, IKO, Atlas, TAMKO, and Malarkey.

You have memorized every color name, shade variation, and product line from each manufacturer.
You understand how shingles age, fade, and wear over time and can accurately assess condition
from photographs.

Your analysis must be precise and grounded in actual manufacturer color names. Do not invent
color names — only return names that exist in the reference list provided.

Always return valid JSON only, with no additional text or explanation outside the JSON object."""


def build_color_reference(colors_data: dict[str, dict[str, list[str]]]) -> str:
    lines = ["Known manufacturer color names (reference these exactly):"]
    for mfr, product_lines in sorted(colors_data.items()):
        for pl, color_names in sorted(product_lines.items()):
            lines.append(f"\n{mfr} - {pl}:")
            lines.append("  " + ", ".join(color_names))
    return "\n".join(lines)


def build_user_prompt(color_reference: str) -> str:
    return f"""Analyze this photograph of asphalt roof shingles.

{color_reference}

{CONDITION_GUIDELINES}

Return ONLY a JSON object with exactly this structure (no markdown, no prose):
{{
  "identified_color_name": "exact official color name from the reference list above",
  "manufacturer_guess": "most likely manufacturer name or null",
  "product_line_guess": "most likely product line or null",
  "condition": "new" or "good" or "worn" or "faded" or "damaged",
  "condition_confidence": 0.0 to 1.0,
  "color_confidence": 0.0 to 1.0,
  "color_reasoning": "2-3 sentences explaining what specific visual features led to this color identification",
  "condition_reasoning": "2-3 sentences explaining the specific visual cues that indicate this condition",
  "alternative_colors": ["second most likely color name", "third most likely color name"]
}}

Be precise. If you cannot confidently identify the color, still pick the closest match but
set color_confidence below 0.6. Never return a color name not in the reference list."""


async def analyze_image(image_bytes: bytes, content_type: str) -> dict:
    """Call Claude Vision API and return parsed JSON result."""
    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    colors_data = await get_all_colors_for_prompt()
    color_reference = build_color_reference(colors_data)
    user_prompt = build_user_prompt(color_reference)

    # Encode image as base64
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Map content type to Anthropic media type
    media_type_map = {
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/webp": "image/webp",
        "image/gif": "image/gif",
    }
    media_type = media_type_map.get(content_type.lower(), "image/jpeg")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text.strip()
    logger.debug("Raw Vision API response: %s", raw_text)

    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Vision API JSON: %s\nRaw: %s", e, raw_text)
        raise ValueError(f"Vision API returned invalid JSON: {e}") from e

    # Validate required fields
    required = [
        "identified_color_name", "condition", "condition_confidence",
        "color_confidence", "color_reasoning", "condition_reasoning",
    ]
    for field in required:
        if field not in result:
            raise ValueError(f"Vision API response missing field: {field}")

    return result
