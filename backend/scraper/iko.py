import logging
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

IKO_PAGES = [
    ("Cambridge", "https://www.iko.com/na/residential/shingles/architectural/cambridge/"),
    ("Dynasty", "https://www.iko.com/na/residential/shingles/architectural/dynasty/"),
    ("Nordic", "https://www.iko.com/na/residential/shingles/3-tab/nordic/"),
]


class IKOScraper(BaseScraper):
    name = "iko"

    async def fetch_colors(self) -> list[dict]:
        results = []
        for product_line, url in IKO_PAGES:
            html = await self.fetch_page(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for selector in [
                ".colour-name", ".color-name", ".swatch-name",
                "[data-colour]", "[data-color]",
            ]:
                items = soup.select(selector)
                if items:
                    for item in items:
                        name = item.get("data-colour") or item.get("data-color") or item.get_text(strip=True)
                        if name and len(name) > 2:
                            results.append({
                                "color_name": name.strip(),
                                "product_line": product_line,
                                "swatch_url": None,
                                "description": None,
                            })
                    break

            logger.info("IKO %s: scrape complete", product_line)

        return results
