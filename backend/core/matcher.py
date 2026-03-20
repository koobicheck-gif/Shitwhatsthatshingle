import logging
from typing import Optional

from rapidfuzz import fuzz, process

from backend.database.queries import find_color_by_name, get_all_colors_for_prompt
from backend.models.response import AlternativeColor, IdentifyResponse

logger = logging.getLogger(__name__)


async def _build_flat_color_list() -> list[dict]:
    """Build a flat list of {color_name, manufacturer, product_line} for fuzzy matching."""
    colors_data = await get_all_colors_for_prompt()
    flat = []
    for mfr, product_lines in colors_data.items():
        for pl, color_names in product_lines.items():
            for name in color_names:
                flat.append({
                    "color_name": name,
                    "manufacturer": mfr,
                    "product_line": pl if pl != "General" else None,
                })
    return flat


async def match_color(
    vision_result: dict,
    include_alternatives: bool = True,
) -> dict:
    """
    Post-process Claude's vision output:
    1. Fuzzy-match the identified color name against the full DB
    2. Compute a blended confidence score
    3. Return a structured dict ready for IdentifyResponse
    """
    identified = vision_result.get("identified_color_name", "")
    claude_color_conf = float(vision_result.get("color_confidence", 0.5))
    claude_cond_conf = float(vision_result.get("condition_confidence", 0.5))
    alternatives_raw = vision_result.get("alternative_colors", [])

    flat_colors = await _build_flat_color_list()
    color_names_only = [c["color_name"] for c in flat_colors]

    # Primary fuzzy match
    best_match = process.extractOne(
        identified,
        color_names_only,
        scorer=fuzz.token_sort_ratio,
    )

    if best_match:
        matched_name, match_score, match_idx = best_match
        match_score_normalized = match_score / 100.0
        matched_record = flat_colors[match_idx]
    else:
        matched_name = identified
        match_score_normalized = 0.0
        matched_record = {"manufacturer": None, "product_line": None}

    logger.debug(
        "Fuzzy match: '%s' -> '%s' (score=%.2f)",
        identified,
        matched_name,
        match_score_normalized,
    )

    # Get hex codes from DB for the matched color
    hex_codes = []
    swatch_url = None
    db_records = await find_color_by_name(matched_name)
    if db_records:
        hex_codes = db_records[0].get("hex_codes", [])
        swatch_url = db_records[0].get("swatch_url")
        # Use DB record's manufacturer/product line if match is strong
        if match_score_normalized >= 0.85:
            matched_record = {
                "manufacturer": db_records[0]["manufacturer"],
                "product_line": db_records[0]["product_line"],
            }

    # Blended confidence score
    final_confidence = (claude_color_conf * 0.7) + (match_score_normalized * 0.3)
    requires_manual_review = final_confidence < 0.6

    # Process alternatives
    alternatives = []
    if include_alternatives:
        alt_names = alternatives_raw[:3] if alternatives_raw else []
        for alt_name in alt_names:
            if not alt_name:
                continue
            alt_match = process.extractOne(
                alt_name, color_names_only, scorer=fuzz.token_sort_ratio
            )
            if alt_match:
                alt_matched, alt_score, alt_idx = alt_match
                alt_record = flat_colors[alt_idx]
                alternatives.append(
                    AlternativeColor(
                        color_name=alt_matched,
                        manufacturer=alt_record.get("manufacturer"),
                        product_line=alt_record.get("product_line"),
                        confidence=round(alt_score / 100.0, 3),
                    )
                )

    hex_preview = hex_codes[0] if hex_codes else None

    return {
        "color_name": matched_name,
        "manufacturer": matched_record.get("manufacturer") or vision_result.get("manufacturer_guess"),
        "product_line": matched_record.get("product_line") or vision_result.get("product_line_guess"),
        "condition": vision_result.get("condition", "unknown"),
        "condition_confidence": round(claude_cond_conf, 3),
        "color_confidence": round(claude_color_conf, 3),
        "final_confidence": round(final_confidence, 3),
        "requires_manual_review": requires_manual_review,
        "hex_preview": hex_preview,
        "color_reasoning": vision_result.get("color_reasoning", ""),
        "condition_reasoning": vision_result.get("condition_reasoning", ""),
        "alternatives": alternatives,
    }
