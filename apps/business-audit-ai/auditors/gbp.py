"""
Google Business Profile (GBP) Auditor — checks whether a business has an optimized GBP.
Missing/incomplete GBP = invisible in Google Maps local pack = lost foot traffic and calls.

Data extracted:
  - Has a GBP at all
  - Star rating + review count
  - Whether hours are listed
  - Whether they respond to reviews
  - Whether they post GBP updates
  - Photo count signal
  - Missing fields

No API key needed — scrapes Google search knowledge panel and DuckDuckGo.
"""
import re
import random
import time
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from typing import Optional


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


class GBPAuditor:
    def __init__(self, business_name: Optional[str], url: str, website_data: dict):
        self.business_name = business_name or self._infer_name(website_data, url)
        self.url = url
        self.website_data = website_data
        # Infer location from competitor module data or website text
        self.location = self._infer_location(website_data)

    def audit(self) -> dict:
        if not self.business_name:
            return {"skipped": True, "reason": "Could not determine business name"}

        # Try multiple search approaches
        result = self._search_gbp()

        issues = self._identify_issues(result)
        result["issues"] = issues
        result["issue_count"] = len(issues)
        result["cold_email_angle"] = self._cold_email_angle(result)
        return result

    def _search_gbp(self) -> dict:
        """Search for GBP via Google search knowledge panel."""
        query = self.business_name
        if self.location:
            query = f"{self.business_name} {self.location}"

        # Try DuckDuckGo first (more scraping-friendly)
        result = self._ddg_search(query)
        if not result.get("gbp_found"):
            time.sleep(random.uniform(0.5, 1.2))
            result = self._google_search(query)

        return result

    def _ddg_search(self, query: str) -> dict:
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            r = requests.get(url, headers=_headers(), timeout=12)
            if r.status_code != 200:
                return {"gbp_found": False, "source": "ddg_failed"}

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text()

            return self._extract_gbp_signals(soup, text, "duckduckgo")
        except Exception:
            return {"gbp_found": False, "source": "ddg_error"}

    def _google_search(self, query: str) -> dict:
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&gl=us&hl=en"
            r = requests.get(url, headers=_headers(), timeout=12)
            if r.status_code != 200:
                return {"gbp_found": False, "source": "google_failed"}

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text()

            return self._extract_gbp_signals(soup, text, "google")
        except Exception:
            return {"gbp_found": False, "source": "google_error"}

    def _extract_gbp_signals(self, soup: BeautifulSoup, text: str, source: str) -> dict:
        result = {"source": source, "gbp_found": False}

        # --- Rating ---
        rating = None
        review_count = None

        # Pattern 1: aria-label with rating (Google knowledge panel)
        for elem in soup.find_all(attrs={"aria-label": True}):
            label = elem.get("aria-label", "")
            m = re.search(r"(?:Rated\s+)?([\d.]+)\s*(?:out of 5|/5|\s*stars?).*?([\d,]+)\s*(?:Google\s+)?reviews?", label, re.I)
            if m:
                rating = float(m.group(1))
                review_count = int(m.group(2).replace(",", ""))
                break

        # Pattern 2: plain text "4.8 (127 reviews)"
        if rating is None:
            m = re.search(r'([\d.]+)\s*[★\*]?\s*[·•\|]?\s*\(?([\d,]+)\s*(?:Google\s+)?review', text, re.I)
            if m:
                try:
                    rating = float(m.group(1))
                    review_count = int(m.group(2).replace(",", ""))
                except ValueError:
                    pass

        # Pattern 3: structured data / JSON-LD
        if rating is None:
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    import json
                    data = json.loads(script.string or "")
                    if isinstance(data, dict):
                        agg = data.get("aggregateRating", {})
                        if agg:
                            rating = float(agg.get("ratingValue", 0)) or None
                            review_count = int(agg.get("reviewCount", 0)) or None
                except Exception:
                    pass

        if rating:
            result["gbp_found"] = True
            result["rating"] = rating
            result["review_count"] = review_count

        # --- Hours listed ---
        hours_patterns = [
            r"open\s+\d+:\d+\s*[ap]m",
            r"closes?\s+at\s+\d+",
            r"monday.*friday",
            r"mon.*fri.*\d+:\d+",
            r"open\s+(?:now|today)",
            r"\d+:\d+\s*(?:am|pm).*\d+:\d+\s*(?:am|pm)",
        ]
        has_hours = any(re.search(p, text, re.I) for p in hours_patterns)
        result["has_hours_listed"] = has_hours

        # --- Website linked ---
        has_website = bool(soup.find("a", href=re.compile(r"website|visit|web", re.I))) or \
                      "website" in text.lower()
        result["has_website_linked"] = has_website

        # --- Photos signal ---
        photo_m = re.search(r'([\d,]+)\s+photos?', text, re.I)
        if photo_m:
            count = int(photo_m.group(1).replace(",", ""))
            result["photo_count"] = count
            result["photos_adequate"] = count >= 10

        # --- GBP posts/updates ---
        has_updates = bool(re.search(r'(?:posted|update|offer|event)\s+\d+\s+(?:day|week|month)', text, re.I))
        result["has_recent_updates"] = has_updates

        # --- Response to reviews ---
        has_responses = bool(re.search(r'response\s+from\s+(?:owner|business)', text, re.I)) or \
                        bool(re.search(r'owner\s+replied', text, re.I))
        result["responds_to_reviews"] = has_responses

        # --- Address / phone presence ---
        result["has_address"] = bool(re.search(r'\d+\s+\w+\s+(?:st|ave|blvd|rd|dr|ln|way)\b', text, re.I)) or \
                                 bool(re.search(r'\b\d{5}(?:-\d{4})?\b', text))
        result["has_phone"] = bool(re.search(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}', text))

        # If we found ANYTHING business-related, mark as found
        if result.get("has_hours_listed") or result.get("has_phone") or result.get("has_address"):
            result["gbp_found"] = True

        return result

    def _identify_issues(self, result: dict) -> list:
        issues = []
        if not result.get("gbp_found"):
            issues.append("No Google Business Profile found — business is invisible in Google Maps / local search")
            return issues  # rest don't apply

        rating = result.get("rating")
        review_count = result.get("review_count", 0) or 0

        if rating and rating < 4.0:
            issues.append(f"Low rating of {rating}/5 — most consumers filter for 4+ stars")
        if review_count < 10:
            issues.append(f"Only {review_count} Google reviews — competitors with 50+ reviews dominate local pack rankings")
        if not result.get("has_hours_listed"):
            issues.append("Business hours not listed — customers can't tell if you're open, causing them to call a competitor")
        if not result.get("responds_to_reviews"):
            issues.append("No review responses detected — unanswered negative reviews cost ~22% of leads (Moz)")
        if not result.get("has_recent_updates"):
            issues.append("No recent GBP posts/updates — businesses that post weekly rank 32% higher in local pack (BrightLocal)")
        photo_count = result.get("photo_count", 0) or 0
        if photo_count < 10:
            issues.append(f"{'No' if photo_count == 0 else 'Few'} photos on GBP — profiles with 100+ photos get 1,065% more website clicks (Google)")

        return issues

    def _cold_email_angle(self, result: dict) -> Optional[str]:
        if not result.get("gbp_found"):
            return f"We couldn't find a Google Business Profile for {self.business_name} — meaning you're invisible in the Google Maps local pack where 46% of all searches go."

        issues = result.get("issues", [])
        if not issues:
            return None

        rating = result.get("rating")
        review_count = result.get("review_count", 0) or 0

        if rating and rating < 4.0:
            return f"Your {rating}/5 Google rating is below the 4.0 threshold — most consumers filter you out before they even see your website."
        if review_count < 10:
            return f"You have {review_count} Google reviews while the top competitor in your area likely has 50+. That gap alone costs you the #1 local pack slot."
        if not result.get("responds_to_reviews"):
            return f"You have {review_count} Google reviews but none appear to have owner responses — unanswered reviews, especially negative ones, cost you ~22% of potential leads."
        return issues[0] if issues else None

    def _infer_name(self, website_data: dict, url: str) -> Optional[str]:
        homepage = website_data.get("homepage", {})
        title = homepage.get("title", "") or ""
        if title:
            # Strip common suffixes
            for suffix in [" - Home", " | Home", " – Home", " | Official", " - Official Website"]:
                title = title.replace(suffix, "")
            return title.strip()[:80]
        return None

    def _infer_location(self, website_data: dict) -> Optional[str]:
        homepage = website_data.get("homepage", {})
        text = homepage.get("text_preview", "") or ""
        m = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b', text)
        if m:
            return f"{m.group(1)}, {m.group(2)}"
        return None
