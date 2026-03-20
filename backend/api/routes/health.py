from fastapi import APIRouter
from backend.database.db import get_color_count
from backend.config import settings
from backend.models.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    count = await get_color_count()
    return HealthResponse(
        status="ok",
        db_color_count=count,
        db_path=settings.db_path,
    )
