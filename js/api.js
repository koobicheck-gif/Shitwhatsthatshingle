'use strict';

const API = (() => {
  const ANTHROPIC_ENDPOINT = 'https://api.anthropic.com/v1/messages';

  const SYSTEM_PROMPT = `You are an expert roofing material identification specialist and color analyst
with 20+ years of experience identifying asphalt shingles from major manufacturers including GAF,
CertainTeed, Owens Corning, IKO, Atlas, TAMKO, and Malarkey.

You have memorized every color name, shade variation, and product line from each manufacturer.
You understand how shingles age, fade, and wear over time and can accurately assess condition
from photographs.

Your analysis must be precise and grounded in actual manufacturer color names. Do not invent
color names — only return names that exist in the reference list provided.

Always return valid JSON only, with no additional text or explanation outside the JSON object.`;

  const CONDITION_GUIDELINES = `Condition definitions (use visual cues):
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
5. Reflection: slight sheen in sunlight = newer; flat/matte = older`;

  let _colorsCache = null;
  let _flatColorsCache = null;

  async function loadColors() {
    if (_colorsCache) return _colorsCache;
    const base = (typeof CONFIG !== 'undefined' && CONFIG.COLORS_BASE_URL)
      ? CONFIG.COLORS_BASE_URL
      : '.';
    const res = await fetch(`${base}/data/colors.json`);
    if (!res.ok) throw new Error('Could not load color database.');
    _colorsCache = await res.json();
    return _colorsCache;
  }

  async function getFlatColors() {
    if (_flatColorsCache) return _flatColorsCache;
    const colors = await loadColors();
    const flat = [];
    for (const [mfr, productLines] of Object.entries(colors)) {
      for (const [pl, colorNames] of Object.entries(productLines)) {
        for (const name of colorNames) {
          flat.push({
            color_name: name,
            manufacturer: mfr,
            product_line: pl === 'General' ? null : pl,
          });
        }
      }
    }
    _flatColorsCache = flat;
    return flat;
  }

  function buildColorReference(colors) {
    const lines = ['Known manufacturer color names (reference these exactly):'];
    for (const mfr of Object.keys(colors).sort()) {
      for (const pl of Object.keys(colors[mfr]).sort()) {
        lines.push(`\n${mfr} - ${pl}:`);
        lines.push('  ' + colors[mfr][pl].join(', '));
      }
    }
    return lines.join('\n');
  }

  // Simple token-overlap fuzzy match, returns 0-1 score
  function tokenScore(a, b) {
    const ta = new Set(a.toLowerCase().split(/\W+/).filter(Boolean));
    const tb = new Set(b.toLowerCase().split(/\W+/).filter(Boolean));
    let shared = 0;
    for (const t of ta) { if (tb.has(t)) shared++; }
    if (ta.size + tb.size === 0) return 0;
    // Also check substring containment for short color names
    const la = a.toLowerCase(), lb = b.toLowerCase();
    if (la === lb) return 1;
    const overlap = (shared * 2) / (ta.size + tb.size);
    const substr = (la.includes(lb) || lb.includes(la)) ? 0.15 : 0;
    return Math.min(1, overlap + substr);
  }

  function findBestMatch(name, flatColors) {
    let bestRecord = null, bestScore = -1;
    for (const record of flatColors) {
      const score = tokenScore(name, record.color_name);
      if (score > bestScore) {
        bestScore = score;
        bestRecord = record;
      }
    }
    return bestRecord ? { record: bestRecord, score: bestScore } : null;
  }

  async function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  async function identifyShingle(imageBlob, includeAlternatives = true) {
    const apiKey = (typeof CONFIG !== 'undefined' ? CONFIG.ANTHROPIC_API_KEY : null);
    if (!apiKey) {
      const err = new Error('Anthropic API key is not configured.');
      err.code = 'API_KEY_NOT_CONFIGURED';
      throw err;
    }

    const [colors, flatColors, imageB64] = await Promise.all([
      loadColors(),
      getFlatColors(),
      blobToBase64(imageBlob),
    ]);

    const colorReference = buildColorReference(colors);

    const userPrompt = `Analyze this photograph of asphalt roof shingles.

${colorReference}

${CONDITION_GUIDELINES}

Return ONLY a JSON object with exactly this structure (no markdown, no prose):
{
  "identified_color_name": "exact official color name from the reference list above",
  "manufacturer_guess": "most likely manufacturer name or null",
  "product_line_guess": "most likely product line or null",
  "condition": "new" or "good" or "worn" or "faded" or "damaged",
  "condition_confidence": 0.0 to 1.0,
  "color_confidence": 0.0 to 1.0,
  "color_reasoning": "2-3 sentences explaining what specific visual features led to this color identification",
  "condition_reasoning": "2-3 sentences explaining the specific visual cues that indicate this condition",
  "alternative_colors": ["second most likely color name", "third most likely color name"]
}

Be precise. If you cannot confidently identify the color, still pick the closest match but
set color_confidence below 0.6. Never return a color name not in the reference list.`;

    const typeMap = {
      'image/jpeg': 'image/jpeg',
      'image/jpg': 'image/jpeg',
      'image/png': 'image/png',
      'image/webp': 'image/webp',
    };
    const mediaType = typeMap[imageBlob.type] || 'image/jpeg';

    const t0 = Date.now();

    const response = await fetch(ANTHROPIC_ENDPOINT, {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
        'anthropic-dangerous-allow-browser': 'true',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 1024,
        system: SYSTEM_PROMPT,
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'image',
                source: { type: 'base64', media_type: mediaType, data: imageB64 },
              },
              { type: 'text', text: userPrompt },
            ],
          },
        ],
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const msg = errData?.error?.message || `API error ${response.status}`;
      const err = new Error(msg);
      err.status = response.status;
      throw err;
    }

    const apiData = await response.json();
    let rawText = apiData.content[0].text.trim();
    rawText = rawText.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');

    let vision;
    try {
      vision = JSON.parse(rawText);
    } catch (e) {
      throw new Error('Failed to parse AI response. Please try again.');
    }

    const identified = vision.identified_color_name || '';
    const match = findBestMatch(identified, flatColors);
    const matched = match
      ? match.record
      : { color_name: identified, manufacturer: null, product_line: null };
    const matchScore = match ? match.score : 0;

    const claudeColorConf = parseFloat(vision.color_confidence) || 0.5;
    const claudeCondConf = parseFloat(vision.condition_confidence) || 0.5;
    const finalConfidence = Math.round((claudeColorConf * 0.7 + matchScore * 0.3) * 1000) / 1000;

    const alternatives = [];
    if (includeAlternatives && Array.isArray(vision.alternative_colors)) {
      for (const altName of vision.alternative_colors.slice(0, 3)) {
        if (!altName) continue;
        const altMatch = findBestMatch(altName, flatColors);
        if (altMatch) {
          alternatives.push({
            color_name: altMatch.record.color_name,
            manufacturer: altMatch.record.manufacturer,
            product_line: altMatch.record.product_line,
            confidence: Math.round(altMatch.score * 1000) / 1000,
          });
        }
      }
    }

    return {
      color_name: matched.color_name,
      manufacturer: matched.manufacturer || vision.manufacturer_guess || null,
      product_line: matched.product_line || vision.product_line_guess || null,
      condition: vision.condition || 'unknown',
      condition_confidence: Math.round(claudeCondConf * 1000) / 1000,
      color_confidence: Math.round(claudeColorConf * 1000) / 1000,
      final_confidence: finalConfidence,
      requires_manual_review: finalConfidence < 0.6,
      hex_preview: null,
      color_reasoning: vision.color_reasoning || '',
      condition_reasoning: vision.condition_reasoning || '',
      alternatives,
      processing_time_ms: Date.now() - t0,
    };
  }

  async function getHealth() {
    return { status: 'ok' };
  }

  return { identifyShingle, getHealth };
})();
