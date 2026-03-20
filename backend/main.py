import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import identify, colors, health
from backend.config import settings
from backend.database.db import seed_from_json, get_color_count

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the database on startup if it has no colors
    count = await get_color_count()
    if count == 0:
        logger.info("Database empty — seeding from %s", settings.seed_path)
        inserted = await seed_from_json()
        logger.info("Seeded %d color records", inserted)
    else:
        logger.info("Database has %d color records", count)
    yield


app = FastAPI(
    title="ShingleID",
    description="Asphalt shingle color and condition identification API for roofing professionals",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(identify.router, prefix="/api", tags=["Identification"])
app.include_router(colors.router, prefix="/api", tags=["Reference Database"])
app.include_router(health.router, prefix="/api", tags=["Health"])

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
