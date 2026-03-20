import asyncio
import json
import logging
import os
from datetime import datetime

import aiosqlite

from backend.config import settings
from backend.database.db import get_db, MANUFACTURER_DISPLAY_NAMES
from backend.scraper.gaf import GAFScraper
from backend.scraper.certainteed import CertainTeedScraper
from backend.scraper.owens_corning import OwensCorningScaper
from backend.scraper.iko import IKOScraper
from backend.scraper.atlas import AtlasScraper

logger = logging.getLogger(__name__)

SCRAPERS = [
    ("gaf", GAFScraper),
    ("certainteed", CertainTeedScraper),
    ("owens_corning", OwensCorningScaper),
    ("iko", IKOScraper),
    ("atlas", AtlasScraper),
]


async def run_scraper(mfr_key: str, scraper_cls) -> list[dict]:
    logger.info("Starting scraper: %s", mfr_key)
    try:
        async with scraper_cls() as scraper:
            colors = await scraper.fetch_colors()
        logger.info("%s: scraped %d colors", mfr_key, len(colors))
        return [(mfr_key, c) for c in colors]
    except Exception as e:
        logger.error("%s scraper failed: %s", mfr_key, e)
        return []


async def upsert_colors(results: list[tuple[str, dict]]):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    inserted = 0
    updated = 0

    try:
        for mfr_key, color in results:
            display_name = MANUFACTURER_DISPLAY_NAMES.get(mfr_key, mfr_key.upper())

            await db.execute(
                "INSERT OR IGNORE INTO manufacturers (name, scraped_at) VALUES (?, ?)",
                (display_name, now),
            )
            await db.execute(
                "UPDATE manufacturers SET scraped_at = ? WHERE name = ?",
                (now, display_name),
            )

            async with db.execute(
                "SELECT id FROM manufacturers WHERE name = ?", (display_name,)
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    continue
                mfr_id = row["id"]

            color_name = color.get("color_name", "").strip()
            if not color_name:
                continue

            normalized = color_name.lower().strip()
            product_line = color.get("product_line")
            swatch_url = color.get("swatch_url")
            description = color.get("description")

            # Fetch hex codes from swatch if URL available
            hex_codes_json = "[]"
            if swatch_url and color.get("hex_codes"):
                hex_codes_json = json.dumps(color["hex_codes"])

            async with db.execute(
                "SELECT id FROM shingle_colors WHERE manufacturer_id = ? AND color_name = ?",
                (mfr_id, color_name),
            ) as cur:
                existing = await cur.fetchone()

            if existing:
                await db.execute(
                    """UPDATE shingle_colors SET
                       product_line = ?, color_name_normalized = ?,
                       swatch_url = COALESCE(?, swatch_url),
                       description = COALESCE(?, description),
                       scraped_at = ?
                       WHERE id = ?""",
                    (product_line, normalized, swatch_url, description, now, existing["id"]),
                )
                updated += 1
            else:
                await db.execute(
                    """INSERT INTO shingle_colors
                       (manufacturer_id, product_line, color_name, color_name_normalized,
                        hex_codes, swatch_url, description, scraped_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mfr_id, product_line, color_name, normalized,
                     hex_codes_json, swatch_url, description, now),
                )
                inserted += 1

        await db.commit()
    finally:
        await db.close()

    return inserted, updated


async def run_all():
    logger.info("Starting full scrape of all manufacturers")
    tasks = [run_scraper(key, cls) for key, cls in SCRAPERS]
    all_results = await asyncio.gather(*tasks)

    flat_results = []
    for r in all_results:
        flat_results.extend(r)

    logger.info("Total colors scraped: %d", len(flat_results))
    inserted, updated = await upsert_colors(flat_results)
    logger.info("DB: %d inserted, %d updated", inserted, updated)
    return inserted, updated
