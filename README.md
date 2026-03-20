# ShingleID

**Professional asphalt shingle color and condition identification for roofing contractors.**

Upload a photograph of a roof and get back:
- The **exact manufacturer color name** (e.g., "Weathered Wood", "Charcoal", "Pewter Gray")
- The **condition** (New / Good / Worn / Faded / Damaged)
- **Visual reasoning** explaining the identification
- **Confidence score** with alternative matches when confidence is lower

Supports shingles from **GAF, CertainTeed, Owens Corning, IKO, Atlas, TAMKO, and Malarkey**.

---

## How It Works

1. **Reference Database** — A SQLite database of ~300+ manufacturer color names is seeded from `data/colors_seed.json` on startup. An optional scraper enriches it with live manufacturer website data.

2. **Claude Vision Analysis** — The uploaded photo is sent to Claude (claude-sonnet-4-6) with the full color name list injected into the prompt, so the AI responds with real manufacturer names rather than generic descriptions.

3. **Fuzzy Matching** — Claude's output is post-processed against the database using fuzzy string matching to canonicalize the result and compute a final confidence score.

---

## Setup

### Requirements
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

### Install

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### Run

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The app auto-seeds the database on first start. Open http://localhost:8000 in your browser.

---

## Optional: Enrich with Live Scraper Data

```bash
python scripts/run_scraper.py
```

This scrapes manufacturer websites for the latest color names and product lines. Results are merged into the existing database without overwriting seed data.

---

## API

### `POST /api/identify`
Upload a shingle photo for identification.

**Request:** `multipart/form-data`
- `image` — JPEG, PNG, or WEBP file (max 10MB)
- `include_alternatives` — bool (default `true`)

**Response:**
```json
{
  "color_name": "Weathered Wood",
  "manufacturer": "GAF",
  "product_line": "Timberline HDZ",
  "condition": "worn",
  "condition_confidence": 0.87,
  "color_confidence": 0.94,
  "final_confidence": 0.91,
  "requires_manual_review": false,
  "hex_preview": "#6b5a3e",
  "color_reasoning": "The shingles show a warm brown-gray blend...",
  "condition_reasoning": "Granule loss visible on exposed edges...",
  "alternatives": [
    {"color_name": "Barkwood", "manufacturer": "GAF", "confidence": 0.71}
  ],
  "processing_time_ms": 2340
}
```

### `GET /api/colors`
Browse the reference color database.

Query params: `?manufacturer=GAF&product_line=Timberline+HDZ&q=weathered&limit=50&offset=0`

### `GET /api/health`
Returns DB status and color count.

---

## Accuracy Notes

- **Best results:** Clear photos taken in natural daylight, shingles filling the frame
- **Confidence ≥ 80%:** High confidence match
- **Confidence 60–79%:** Good match, check alternatives
- **Confidence < 60%:** `requires_manual_review: true` — take a clearer photo or consult alternatives
- Worn and faded shingles may show slightly lower confidence because colors shift over time

### On Facebook Group Data
Facebook's API requires app review and restricts access to group content. Scraping Facebook groups would violate their Terms of Service. The manufacturer databases and Claude Vision together provide the accuracy target. A future user-contribution model would be the compliant path for community data.

---

## Project Structure

```
backend/
  main.py          # FastAPI app entry point
  config.py        # Settings and env var loading
  core/
    vision.py      # Claude Vision API client + prompt engineering
    matcher.py     # Fuzzy string matching against color DB
  api/routes/      # REST endpoints
  database/        # SQLite schema and queries
  scraper/         # Manufacturer color scrapers
data/
  colors_seed.json # ~300 curated manufacturer colors (committed)
  colors.db        # SQLite database (generated, gitignored)
frontend/          # Vanilla JS + CSS, served by FastAPI
scripts/           # seed_db.py, run_scraper.py
```
