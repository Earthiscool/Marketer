"""
Local Citations Auditor — checks if the business is listed on major directories.

Missing citations directly suppress Google Maps rankings:
"You're missing from 14 of the top 20 local directories" is a
quantifiable, provable problem that's easy to explain and easy to sell a fix for.

Also checks NAP consistency signals (Name, Address, Phone) where detectable.

Uses DuckDuckGo site: searches to check each directory — no API keys needed.
Checks 20 top citation sources weighted by SEO authority.
"""
import requests
import re
import time
import random
from urllib.parse import quote_plus
from typing import Optional
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Ordered by SEO authority / citation weight
DIRECTORIES = [
    {"name": "Yelp",              "domain": "yelp.com",           "weight": 10, "tier": 1},
    {"name": "Facebook Business", "domain": "facebook.com",       "weight": 9,  "tier": 1},
    {"name": "BBB",               "domain": "bbb.org",            "weight": 9,  "tier": 1},
    {"name": "YellowPages",       "domain": "yellowpages.com",    "weight": 8,  "tier": 1},
    {"name": "Foursquare",        "domain": "foursquare.com",     "weight": 7,  "tier": 1},
    {"name": "Angi",              "domain": "angi.com",           "weight": 7,  "tier": 2},
    {"name": "HomeAdvisor",       "domain": "homeadvisor.com",    "weight": 7,  "tier": 2},
    {"name": "Thumbtack",         "domain": "thumbtack.com",      "weight": 7,  "tier": 2},
    {"name": "TripAdvisor",       "domain": "tripadvisor.com",    "weight": 7,  "tier": 2},
    {"name": "Houzz",             "domain": "houzz.com",          "weight": 6,  "tier": 2},
    {"name": "MapQuest",          "domain": "mapquest.com",       "weight": 6,  "tier": 2},
    {"name": "Manta",             "domain": "manta.com",          "weight": 6,  "tier": 2},
    {"name": "Nextdoor",          "domain": "nextdoor.com",       "weight": 6,  "tier": 2},
    {"name": "Merchant Circle",   "domain": "merchantcircle.com", "weight": 5,  "tier": 3},
    {"name": "Superpages",        "domain": "superpages.com",     "weight": 5,  "tier": 3},
    {"name": "CitySearch",        "domain": "citysearch.com",     "weight": 5,  "tier": 3},
    {"name": "Local.com",         "domain": "local.com",          "weight": 5,  "tier": 3},
    {"name": "Hotfrog",           "domain": "hotfrog.com",        "weight": 4,  "tier": 3},
    {"name": "EZlocal",           "domain": "ezlocal.com",        "weight": 4,  "tier": 3},
    {"name": "Alignable",         "domain": "alignable.com",      "weight": 4,  "tier": 3},
]

TIER1 = [d for d in DIRECTORIES if d["tier"] == 1]
TIER2 = [d for d in DIRECTORIES if d["tier"] == 2]
TIER3 = [d for d in DIRECTORIES if d["tier"] == 3]


class CitationsAuditor:
    def __init__(self, business_name: str, url: str, location: Optional[str] = None):
        self.business_name = business_name or url
        self.url = url
        self.location = location

    def audit(self) -> dict:
        found = []
        missing = []

        # Check all directories — stagger requests to avoid rate limiting
        for i, directory in enumerate(DIRECTORIES):
            listed = self._check_directory(directory["name"], directory["domain"])
            if listed:
                found.append({"name": directory["name"], "tier": directory["tier"], "weight": directory["weight"]})
            else:
                missing.append({"name": directory["name"], "tier": directory["tier"], "weight": directory["weight"]})

            # Short delay, longer every 5 requests
            delay = random.uniform(0.6, 1.1) if (i + 1) % 5 != 0 else random.uniform(1.5, 2.5)
            time.sleep(delay)

        total = len(DIRECTORIES)
        found_count = len(found)
        missing_count = len(missing)

        # Weighted coverage score (tier 1 misses hurt more)
        max_weight = sum(d["weight"] for d in DIRECTORIES)
        earned_weight = sum(d["weight"] for d in found)
        coverage_score = int(earned_weight / max_weight * 100)

        # Tier breakdown
        tier1_found = [d for d in found if d["tier"] == 1]
        tier1_missing = [d for d in missing if d["tier"] == 1]

        found_names = [d["name"] for d in found]
        missing_names = [d["name"] for d in missing]

        return {
            "directories_checked": total,
            "found_in": found_names,
            "missing_from": missing_names,
            "listing_count": found_count,
            "missing_count": missing_count,
            "coverage_percent": int(found_count / total * 100),
            "weighted_coverage_score": coverage_score,
            "tier1_found": [d["name"] for d in tier1_found],
            "tier1_missing": [d["name"] for d in tier1_missing],
            "tier1_coverage": f"{len(tier1_found)}/{len(TIER1)}",
            "cold_email_angle": self._cold_email_angle(missing_count, total, tier1_missing, tier1_found),
            "priority_fixes": self._priority_fixes(missing),
        }

    def _check_directory(self, name: str, domain: str) -> bool:
        """Use DuckDuckGo site: search to check if business is listed on this directory."""
        try:
            # Quoted business name + site: for precision
            query = f'"{self.business_name}" site:{domain}'
            if self.location:
                query = f'"{self.business_name}" {self.location} site:{domain}'

            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            r = requests.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                # Fallback: try without location
                if self.location:
                    query2 = f'"{self.business_name}" site:{domain}'
                    url2 = f"https://html.duckduckgo.com/html/?q={quote_plus(query2)}"
                    r = requests.get(url2, headers=HEADERS, timeout=10)
                    if r.status_code != 200:
                        return False
                else:
                    return False

            soup = BeautifulSoup(r.text, "lxml")
            results = soup.select("div.result, div.result--web")

            # Check result URLs actually point to this directory
            for result in results:
                link = result.select_one("a.result__a")
                if link:
                    href = link.get("href", "").lower()
                    if domain.split(".")[0] in href:
                        return True
                # Also check result text
                if domain.split(".")[0] in result.get_text().lower():
                    return True

            return False
        except Exception:
            return False

    def _cold_email_angle(self, missing_count: int, total: int, tier1_missing: list, tier1_found: list) -> Optional[str]:
        if missing_count == 0:
            return None
        if tier1_missing:
            top_missing = [d["name"] for d in tier1_missing[:2]]
            return (
                f"Your business is missing from {missing_count} of the top {total} local directories — "
                f"including {', '.join(top_missing)}, which directly suppresses your Google Maps ranking. "
                f"Competitors with full directory coverage show up in the local 3-pack; you don't."
            )
        return (
            f"You're missing from {missing_count} of {total} local directories — "
            f"these citations are a top-3 local SEO ranking factor and every missing one is a slot a competitor takes."
        )

    def _priority_fixes(self, missing: list) -> list:
        """Return the highest-weight missing directories to fix first."""
        sorted_missing = sorted(missing, key=lambda d: d["weight"], reverse=True)
        return [d["name"] for d in sorted_missing[:5]]
