#!/usr/bin/env python3
"""Run all manufacturer scrapers to enrich the color database with live data."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from backend.scraper.runner import run_all
from backend.database.db import get_color_count


async def main():
    print("Running all manufacturer scrapers...")
    print("This may take a few minutes (respectful rate limiting applied).")
    print()

    inserted, updated = await run_all()

    total = await get_color_count()
    print()
    print(f"Scrape complete.")
    print(f"  Inserted: {inserted} new colors")
    print(f"  Updated:  {updated} existing colors")
    print(f"  Total in DB: {total}")


if __name__ == "__main__":
    asyncio.run(main())
