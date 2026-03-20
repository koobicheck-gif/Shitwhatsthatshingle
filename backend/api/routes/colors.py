from fastapi import APIRouter, Query
from typing import Optional
from backend.database.queries import get_colors_paginated
from backend.models.response import ColorRecord

router = APIRouter()


@router.get("/colors", response_model=list[ColorRecord])
async def list_colors(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer name"),
    product_line: Optional[str] = Query(None, description="Filter by product line"),
    q: Optional[str] = Query(None, description="Search color names"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    rows = await get_colors_paginated(
        manufacturer=manufacturer,
        product_line=product_line,
        query=q,
        limit=limit,
        offset=offset,
    )
    return [ColorRecord(**row) for row in rows]
