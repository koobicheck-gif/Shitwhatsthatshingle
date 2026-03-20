import logging
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

ATLAS_PAGES = [
    ("StormMaster Shake", "https://www.atlasroofing.com/products/stormmaster-shake"),
    ("StormMaster Slate", "https://www.atlasroofing.com/products/stormmaster-slate"),
    ("Pinnacle Pristine", "https://www.atlasroofing.com/products/pinnacle-pristine"),
]


class AtlasScraper(BaseScraper):
    name = "atlas"

    async def fetch_colors(self) -> list[dict]:
        results = []
        for product_line, url in ATLAS_PAGES:
            html = await self.fetch_page(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for selector in [
                ".color-name", ".swatch-title", ".product-color__label",
                "[data-color-name]", ".colour-title",
            ]:
                items = soup.select(selector)
                if items:
                    for item in items:
                        name = item.get("data-color-name") or item.get_text(strip=True)
                        if name and len(name) > 2:
                            results.append({
                                "color_name": name.strip(),
                                "product_line": product_line,
                                "swatch_url": None,
                                "description": None,
                            })
                    break

            logger.info("Atlas %s: scrape complete", product_line)

        return results
