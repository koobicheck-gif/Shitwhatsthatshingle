#!/usr/bin/env python3
"""Populate the SQLite database from the static colors_seed.json file."""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import seed_from_json, get_color_count


async def main():
    print("Seeding database from colors_seed.json...")
    inserted = await seed_from_json()
    total = await get_color_count()
    print(f"Done. Inserted: {inserted} records. Total in DB: {total}")


if __name__ == "__main__":
    asyncio.run(main())
