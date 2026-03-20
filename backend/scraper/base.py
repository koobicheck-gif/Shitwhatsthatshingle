import asyncio
import io
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class BaseScraper(ABC):
    name: str = "base"
    delay_seconds: float = 1.5

    def __init__(self):
        self.client = httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    @abstractmethod
    async def fetch_colors(self) -> list[dict]:
        """Return list of {color_name, product_line, swatch_url, description}."""

    async def fetch_page(self, url: str) -> Optional[str]:
        try:
            await asyncio.sleep(self.delay_seconds)
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as e:
            logger.warning("%s: failed to fetch %s: %s", self.name, url, e)
            return None

    async def download_swatch(self, url: str) -> Optional[bytes]:
        try:
            await asyncio.sleep(0.5)
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPError as e:
            logger.warning("%s: failed to download swatch %s: %s", self.name, url, e)
            return None

    def sample_hex_from_swatch(self, image_bytes: bytes, n_colors: int = 3) -> list[str]:
        """Sample dominant hex colors from a swatch image using PIL."""
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = img.resize((50, 50))
            pixels = list(img.getdata())

            # Simple median cut: just sample from center pixels
            center_pixels = [
                pixels[i]
                for i in range(len(pixels))
                if abs(i % 50 - 25) < 10 and abs(i // 50 - 25) < 10
            ]
            if not center_pixels:
                center_pixels = pixels[:100]

            # Average the center pixels for a representative color
            r = sum(p[0] for p in center_pixels) // len(center_pixels)
            g = sum(p[1] for p in center_pixels) // len(center_pixels)
            b = sum(p[2] for p in center_pixels) // len(center_pixels)
            return [f"#{r:02x}{g:02x}{b:02x}"]
        except Exception as e:
            logger.debug("Could not sample hex from swatch: %s", e)
            return []
