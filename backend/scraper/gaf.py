import logging
import re
from bs4 import BeautifulSoup
from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)

# GAF product pages that list colors
GAF_COLOR_PAGES = [
    ("Timberline HDZ", "https://www.gaf.com/en-us/roofing-products/residential-roofing/shingles/timberline-hdz-shingles"),
    ("Timberline CS", "https://www.gaf.com/en-us/roofing-products/residential-roofing/shingles/timberline-cs-shingles"),
    ("Camelot II", "https://www.gaf.com/en-us/roofing-products/residential-roofing/shingles/camelot-ii-shingles"),
    ("Royal Sovereign", "https://www.gaf.com/en-us/roofing-products/residential-roofing/shingles/royal-sovereign-shingles"),
]


class GAFScraper(BaseScraper):
    name = "gaf"

    async def fetch_colors(self) -> list[dict]:
        results = []
        for product_line, url in GAF_COLOR_PAGES:
            html = await self.fetch_page(url)
            if not html:
                logger.warning("GAF: no HTML for %s", product_line)
                continue

            soup = BeautifulSoup(html, "html.parser")

            # GAF uses color swatches with data-color or aria-label attributes
            color_items = []

            # Try multiple selector patterns GAF has used
            for selector in [
                "[data-color-name]",
                ".color-swatch",
                ".product-color__name",
                "[class*='color'] [class*='name']",
            ]:
                items = soup.select(selector)
                if items:
                    color_items = items
                    break

            # Fallback: look for option elements in color selectors
            if not color_items:
                selects = soup.find_all("select", {"id": re.compile(r"color", re.I)})
                for sel in selects:
                    for option in sel.find_all("option"):
                        name = option.get_text(strip=True)
                        if name and name.lower() not in ("select a color", "choose", ""):
                            results.append({
                                "color_name": name,
                                "product_line": product_line,
                                "swatch_url": None,
                                "description": None,
                            })

            for item in color_items:
                name = (
                    item.get("data-color-name")
                    or item.get("aria-label")
                    or item.get_text(strip=True)
                )
                swatch_url = None
                img = item.find("img")
                if img:
                    swatch_url = img.get("src") or img.get("data-src")

                if name and len(name) > 2:
                    results.append({
                        "color_name": name.strip(),
                        "product_line": product_line,
                        "swatch_url": swatch_url,
                        "description": None,
                    })

            logger.info("GAF %s: found %d colors", product_line, len(results))

        return results
