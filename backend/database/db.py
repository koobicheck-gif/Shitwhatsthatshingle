import aiosqlite
import json
import os
from backend.config import settings

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    scraped_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shingle_colors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
    product_line TEXT,
    color_name TEXT NOT NULL,
    color_name_normalized TEXT NOT NULL,
    hex_codes TEXT DEFAULT '[]',
    swatch_url TEXT,
    swatch_local_path TEXT,
    description TEXT,
    scraped_at TIMESTAMP,
    UNIQUE(manufacturer_id, color_name)
);

CREATE INDEX IF NOT EXISTS idx_color_normalized
    ON shingle_colors(color_name_normalized);
"""

MANUFACTURER_WEBSITES = {
    "gaf": "https://www.gaf.com",
    "certainteed": "https://www.certainteed.com",
    "owens_corning": "https://www.owenscorning.com",
    "iko": "https://www.iko.com",
    "atlas": "https://www.atlasroofing.com",
    "tamko": "https://www.tamko.com",
    "malarkey": "https://www.malarkeyroofing.com",
}

MANUFACTURER_DISPLAY_NAMES = {
    "gaf": "GAF",
    "certainteed": "CertainTeed",
    "owens_corning": "Owens Corning",
    "iko": "IKO",
    "atlas": "Atlas",
    "tamko": "TAMKO",
    "malarkey": "Malarkey",
}


async def get_db():
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    await db.executescript(CREATE_TABLES)
    await db.commit()
    return db


async def seed_from_json():
    if not os.path.exists(settings.seed_path):
        return 0

    with open(settings.seed_path) as f:
        data = json.load(f)

    db = await get_db()
    inserted = 0
    try:
        for mfr_key, product_lines in data.items():
            display_name = MANUFACTURER_DISPLAY_NAMES.get(mfr_key, mfr_key.upper())
            website = MANUFACTURER_WEBSITES.get(mfr_key)

            await db.execute(
                "INSERT OR IGNORE INTO manufacturers (name, website) VALUES (?, ?)",
                (display_name, website),
            )
            await db.commit()

            async with db.execute(
                "SELECT id FROM manufacturers WHERE name = ?", (display_name,)
            ) as cur:
                row = await cur.fetchone()
                mfr_id = row["id"]

            for product_line, colors in product_lines.items():
                for color_name in colors:
                    normalized = color_name.lower().strip()
                    try:
                        await db.execute(
                            """INSERT OR IGNORE INTO shingle_colors
                               (manufacturer_id, product_line, color_name, color_name_normalized)
                               VALUES (?, ?, ?, ?)""",
                            (mfr_id, product_line, color_name, normalized),
                        )
                        inserted += 1
                    except Exception:
                        pass

        await db.commit()
    finally:
        await db.close()

    return inserted


async def get_color_count() -> int:
    db = await get_db()
    try:
        async with db.execute("SELECT COUNT(*) as c FROM shingle_colors") as cur:
            row = await cur.fetchone()
            return row["c"]
    finally:
        await db.close()
