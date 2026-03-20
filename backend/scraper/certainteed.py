import logging
import re
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

CERTAINTEED_PAGES = [
    ("Landmark", "https://www.certainteed.com/roofing/products/landmark-shingles/"),
    ("Landmark Pro", "https://www.certainteed.com/roofing/products/landmark-pro-shingles/"),
    ("Landmark Premium", "https://www.certainteed.com/roofing/products/landmark-premium-shingles/"),
    ("Presidential Shake TL", "https://www.certainteed.com/roofing/products/presidential-shake-tl/"),
]


class CertainTeedScraper(BaseScraper):
    name = "certainteed"

    async def fetch_colors(self) -> list[dict]:
        results = []
        for product_line, url in CERTAINTEED_PAGES:
            html = await self.fetch_page(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for selector in [
                ".color-name",
                ".swatch-name",
                "[data-color]",
                ".product-color",
                "li[class*='color']",
            ]:
                items = soup.select(selector)
                if items:
                    for item in items:
                        name = item.get("data-color") or item.get_text(strip=True)
                        if name and len(name) > 2:
                            results.append({
                                "color_name": name.strip(),
                                "product_line": product_line,
                                "swatch_url": None,
                                "description": None,
                            })
                    break

            logger.info("CertainTeed %s: found %d colors total so far", product_line, len(results))

        return results
