import aiosqlite
import json
from backend.database.db import get_db


async def get_all_colors_for_prompt() -> dict[str, dict[str, list[str]]]:
    """Returns {manufacturer_name: {product_line: [color_names]}} for prompt injection."""
    db = await get_db()
    result: dict[str, dict[str, list[str]]] = {}
    try:
        async with db.execute(
            """SELECT m.name as mfr, sc.product_line, sc.color_name
               FROM shingle_colors sc
               JOIN manufacturers m ON m.id = sc.manufacturer_id
               ORDER BY m.name, sc.product_line, sc.color_name"""
        ) as cur:
            async for row in cur:
                mfr = row["mfr"]
                pl = row["product_line"] or "General"
                if mfr not in result:
                    result[mfr] = {}
                if pl not in result[mfr]:
                    result[mfr][pl] = []
                result[mfr][pl].append(row["color_name"])
    finally:
        await db.close()
    return result


async def find_color_by_name(color_name: str) -> list[dict]:
    """Returns all DB records matching or containing the given color name."""
    db = await get_db()
    rows = []
    try:
        normalized = color_name.lower().strip()
        async with db.execute(
            """SELECT sc.id, m.name as manufacturer, sc.product_line,
                      sc.color_name, sc.color_name_normalized,
                      sc.hex_codes, sc.swatch_url
               FROM shingle_colors sc
               JOIN manufacturers m ON m.id = sc.manufacturer_id
               WHERE sc.color_name_normalized LIKE ?
               ORDER BY m.name""",
            (f"%{normalized}%",),
        ) as cur:
            async for row in cur:
                rows.append({
                    "id": row["id"],
                    "manufacturer": row["manufacturer"],
                    "product_line": row["product_line"],
                    "color_name": row["color_name"],
                    "color_name_normalized": row["color_name_normalized"],
                    "hex_codes": json.loads(row["hex_codes"] or "[]"),
                    "swatch_url": row["swatch_url"],
                })
    finally:
        await db.close()
    return rows


async def get_colors_paginated(
    manufacturer: str | None = None,
    product_line: str | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    db = await get_db()
    rows = []
    conditions = []
    params = []

    if manufacturer:
        conditions.append("m.name LIKE ?")
        params.append(f"%{manufacturer}%")
    if product_line:
        conditions.append("sc.product_line LIKE ?")
        params.append(f"%{product_line}%")
    if query:
        conditions.append("sc.color_name_normalized LIKE ?")
        params.append(f"%{query.lower()}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])

    try:
        async with db.execute(
            f"""SELECT sc.id, m.name as manufacturer, sc.product_line,
                       sc.color_name, sc.hex_codes, sc.swatch_url
                FROM shingle_colors sc
                JOIN manufacturers m ON m.id = sc.manufacturer_id
                {where}
                ORDER BY m.name, sc.product_line, sc.color_name
                LIMIT ? OFFSET ?""",
            params,
        ) as cur:
            async for row in cur:
                rows.append({
                    "id": row["id"],
                    "manufacturer": row["manufacturer"],
                    "product_line": row["product_line"],
                    "color_name": row["color_name"],
                    "hex_codes": json.loads(row["hex_codes"] or "[]"),
                    "swatch_url": row["swatch_url"],
                })
    finally:
        await db.close()
    return rows
