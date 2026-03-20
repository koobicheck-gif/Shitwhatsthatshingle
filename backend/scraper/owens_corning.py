import logging
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

OC_PAGES = [
    ("Duration", "https://www.owenscorning.com/en-us/roofing/shingles/duration"),
    ("TruDefinition Duration", "https://www.owenscorning.com/en-us/roofing/shingles/trudefinition-duration"),
    ("Oakridge", "https://www.owenscorning.com/en-us/roofing/shingles/oakridge"),
    ("Berkshire", "https://www.owenscorning.com/en-us/roofing/shingles/berkshire"),
]


class OwensCorningScaper(BaseScraper):
    name = "owens_corning"

    async def fetch_colors(self) -> list[dict]:
        results = []
        for product_line, url in OC_PAGES:
            html = await self.fetch_page(url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for selector in [
                ".color-chip__name",
                ".color-selector__label",
                "[data-color-name]",
                ".swatch-label",
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

            logger.info("Owens Corning %s: scrape complete", product_line)

        return results
