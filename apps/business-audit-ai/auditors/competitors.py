"""
Competitor Intelligence — finds top competitors automatically and compares
them against the target business across every dimension.
"""
import requests
import re
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus, parse_qs, unquote
from typing import Optional


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }


class CompetitorAuditor:
    def __init__(self, url: str, business_name: Optional[str], website_data: dict):
        self.url = url
        self.domain = urlparse(url).netloc
        self.business_name = business_name
        self.website_data = website_data

    def audit(self) -> dict:
        business_type = self._infer_business_type()
        location = self._infer_location()
        competitors = self._find_competitors(business_type, location)
        comparison = self._compare_competitors(competitors)

        return {
            "inferred_business_type": business_type,
            "inferred_location": location,
            "competitors_found": competitors,
            "comparison": comparison,
            "gaps": self._identify_gaps(comparison),
        }

    def _infer_business_type(self) -> str:
        homepage = self.website_data.get("homepage", {})
        title = homepage.get("title", "") or ""
        h1s = homepage.get("h1_tags", [])
        h2s = homepage.get("h2_tags", [])
        preview = homepage.get("text_preview", "") or ""
        all_text = f"{title} {' '.join(h1s)} {' '.join(h2s)} {preview[:300]}".lower()

        categories = {
            "pet store": ["pet", "animal", "dog food", "cat food", "aquarium", "reptile"],
            "plumbing": ["plumb", "pipe", "drain", "water heater"],
            "restaurant": ["restaurant", "menu", "dining", "food", "eat", "chef"],
            "law firm": ["attorney", "lawyer", "legal", "law firm"],
            "dental": ["dental", "dentist", "teeth", "orthodontic"],
            "real estate": ["real estate", "realtor", "homes for sale", "property"],
            "HVAC": ["hvac", "heating", "cooling", "air conditioning"],
            "roofing": ["roof", "roofing", "shingle", "gutter"],
            "landscaping": ["landscap", "lawn", "garden", "mowing"],
            "accounting": ["accounting", "tax", "cpa", "bookkeeping"],
            "marketing agency": ["marketing", "agency", "digital", "branding"],
            "software": ["software", "app", "platform", "saas"],
            "e-commerce": ["shop", "store", "buy", "cart", "product"],
            "fitness": ["gym", "fitness", "workout", "personal trainer"],
            "salon": ["salon", "hair", "beauty", "spa", "nail"],
            "medical": ["medical", "clinic", "doctor", "physician", "healthcare"],
            "insurance": ["insurance", "coverage", "policy", "premium"],
            "construction": ["construction", "contractor", "builder", "remodel"],
            "cleaning": ["cleaning", "janitorial", "maid", "housekeeping"],
        }

        for category, keywords in categories.items():
            if any(kw in all_text for kw in keywords):
                return category

        return self.business_name or "local business"

    def _infer_location(self) -> Optional[str]:
        homepage = self.website_data.get("homepage", {})
        preview = homepage.get("text_preview", "") or ""
        city_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s+([A-Z]{2})\b', preview)
        if city_match:
            return f"{city_match.group(1)}, {city_match.group(2)}"
        state_match = re.search(r'\b([A-Z]{2})\s+\d{5}\b', preview)
        if state_match:
            return state_match.group(1)
        return None

    def _find_competitors(self, business_type: str, location: Optional[str]) -> list:
        queries = []
        if location:
            queries.append(f"best {business_type} {location}")
            queries.append(f"top {business_type} near {location}")
        queries.append(f"top {business_type} companies")
        queries.append(f"{business_type} near me")

        for query in queries:
            results = self._duckduckgo_search(query)
            if results:
                return results
            time.sleep(random.uniform(0.8, 1.5))
            results = self._bing_search(query)
            if results:
                return results
            time.sleep(random.uniform(0.8, 1.5))

        return []

    def _extract_real_url(self, href: str) -> str:
        """Extract the actual destination URL from a DDG redirect link."""
        if href.startswith("//"):
            href = "https:" + href
        if "uddg=" in href:
            try:
                qs = parse_qs(urlparse(href).query)
                urls = qs.get("uddg", [])
                if urls:
                    return unquote(urls[0])
            except Exception:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    return unquote(m.group(1))
        return href

    def _duckduckgo_search(self, query: str) -> list:
        """DuckDuckGo HTML search — bot-detection-free, no API key needed."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            r = requests.get(url, headers=random_headers(), timeout=14)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "lxml")
            competitors = []
            seen_domains = {self.domain, "duckduckgo.com", "yelp.com", "yellowpages.com",
                            "bbb.org", "facebook.com", "wikipedia.org", "tripadvisor.com",
                            "google.com", "linkedin.com", "instagram.com"}

            for result in soup.select("div.result, div.result--web"):
                link = result.select_one("a.result__a")
                if not link:
                    continue

                href = self._extract_real_url(link.get("href", ""))
                if not href.startswith("http"):
                    continue

                parsed = urlparse(href)
                domain = parsed.netloc.replace("www.", "")
                if not domain or any(skip in domain for skip in seen_domains):
                    continue
                seen_domains.add(domain)

                snippet_el = result.select_one("a.result__snippet")
                competitors.append({
                    "name": link.get_text(strip=True),
                    "url": href,
                    "domain": domain,
                    "snippet": snippet_el.get_text(strip=True)[:200] if snippet_el else "",
                })
                if len(competitors) >= 4:
                    break

            return competitors
        except Exception:
            return []

    def _bing_search(self, query: str) -> list:
        """Bing HTML search — fallback if DuckDuckGo yields nothing."""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count=10"
            r = requests.get(url, headers=random_headers(), timeout=14)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "lxml")
            competitors = []
            seen_domains = {self.domain, "bing.com", "yelp.com", "yellowpages.com",
                            "bbb.org", "facebook.com", "wikipedia.org", "tripadvisor.com",
                            "google.com", "linkedin.com", "instagram.com"}

            for li in soup.select("li.b_algo"):
                h2 = li.find("h2")
                if not h2:
                    continue
                a = h2.find("a")
                if not a:
                    continue
                href = a.get("href", "")
                if not href.startswith("http"):
                    continue
                parsed = urlparse(href)
                domain = parsed.netloc.replace("www.", "")
                if not domain or any(skip in domain for skip in seen_domains):
                    continue
                seen_domains.add(domain)

                snippet_el = li.select_one("p, .b_caption p")
                competitors.append({
                    "name": a.get_text(strip=True),
                    "url": href,
                    "domain": domain,
                    "snippet": snippet_el.get_text(strip=True)[:200] if snippet_el else "",
                })
                if len(competitors) >= 4:
                    break

            return competitors
        except Exception:
            return []

    def _compare_competitors(self, competitors: list) -> list:
        results = []
        for comp in competitors:
            time.sleep(random.uniform(0.5, 1.5))
            data = self._quick_audit(comp)
            data.update(comp)
            results.append(data)
        return results

    def _quick_audit(self, comp: dict) -> dict:
        url = comp.get("url", "")
        name = comp.get("name", "")
        try:
            r = requests.get(url, headers=random_headers(), timeout=10, allow_redirects=True)
            if r.status_code != 200:
                data = {"accessible": False}
                data.update(self._scrape_competitor_rating(name))
                return data

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text().lower()
            html = str(soup)

            social_platforms = [p for p in ["facebook.com", "instagram.com", "linkedin.com", "twitter.com", "youtube.com"]
                                 if p in html.lower()]

            result = {
                "accessible": True,
                "has_blog": bool(re.search(r'blog|articles?|news|insights?', html, re.I)),
                "has_live_chat": any(w in html.lower() for w in ["intercom", "drift", "crisp", "tawk", "tidio", "hubspot-messages"]),
                "has_video": bool(soup.find_all(["video", "iframe"])),
                "social_platforms": social_platforms,
                "has_testimonials": "testimonial" in text or bool(soup.find_all("blockquote")),
                "has_pricing": bool(re.search(r'\$\d+|pricing|per month|/mo', text)),
                "has_booking": any(w in html.lower() for w in ["calendly", "acuity", "booking", "appointlet"]),
                "has_free_offer": any(w in text for w in ["free consultation", "free quote", "free trial"]),
                "has_analytics": "gtag" in html or "google-analytics" in html,
                "word_count": len(soup.get_text().split()),
                "cms": self._detect_cms(html),
            }
            result.update(self._scrape_competitor_rating(name))
            return result
        except Exception:
            data = {"accessible": False}
            data.update(self._scrape_competitor_rating(name))
            return data

    def _scrape_competitor_rating(self, name: str) -> dict:
        """Quick Google scrape to get competitor rating + review count."""
        if not name:
            return {"rating": None, "review_count": None}
        try:
            time.sleep(random.uniform(0.5, 1.2))
            query = f"{name} reviews google rating"
            r = requests.get(
                f"https://www.google.com/search?q={quote_plus(query)}",
                headers=random_headers(), timeout=8
            )
            soup = BeautifulSoup(r.text, "lxml")
            rating = None
            review_count = None

            for elem in soup.find_all(attrs={"aria-label": True}):
                label = elem.get("aria-label", "")
                m = re.search(r"Rated ([\d.]+) out of 5.*?([\d,]+)", label, re.I)
                if m:
                    rating = float(m.group(1))
                    review_count = int(m.group(2).replace(",", ""))
                    break

            if rating is None:
                # Try plain text patterns
                text = soup.get_text()
                m = re.search(r'([\d.]+)\s*/\s*5\s*[·•\-]?\s*([\d,]+)\s*(review|rating)', text, re.I)
                if m:
                    rating = float(m.group(1))
                    review_count = int(m.group(2).replace(",", ""))

            return {"rating": rating, "review_count": review_count}
        except Exception:
            return {"rating": None, "review_count": None}

    def _detect_cms(self, html: str) -> str:
        for cms, pat in [("WordPress", "wp-content"), ("Shopify", "shopify"),
                         ("Squarespace", "squarespace"), ("Wix", "wix.com"),
                         ("Webflow", "webflow"), ("Framer", "framer")]:
            if pat in html.lower():
                return cms
        return "unknown"

    def _identify_gaps(self, comparison: list) -> dict:
        accessible = [c for c in comparison if c.get("accessible")]
        if not accessible:
            return {"gaps_vs_competitors": [], "total_competitors_analyzed": 0}

        target_conv = self.website_data.get("conversion_signals", {})
        target_content = self.website_data.get("content_signals", {})
        target_trust = self.website_data.get("trust_signals", {})
        total = len(accessible)

        def pct(key):
            return sum(1 for c in accessible if c.get(key)) / total

        gaps = []
        if pct("has_live_chat") >= 0.5 and not target_conv.get("has_chat_widget"):
            gaps.append({"feature": "Live chat", "competitors_have": f"{int(pct('has_live_chat')*total)}/{total}", "impact": "40% higher conversion (Forrester)"})
        if pct("has_blog") >= 0.5 and not target_content.get("has_blog"):
            gaps.append({"feature": "Blog / content marketing", "competitors_have": f"{int(pct('has_blog')*total)}/{total}", "impact": "67% more leads (HubSpot)"})
        if pct("has_free_offer") >= 0.5 and not target_conv.get("has_free_offer"):
            gaps.append({"feature": "Free consultation offer", "competitors_have": f"{int(pct('has_free_offer')*total)}/{total}", "impact": "2-3x higher CTA conversion"})
        if pct("has_booking") >= 0.5 and not target_conv.get("booking_system"):
            gaps.append({"feature": "Online booking", "competitors_have": f"{int(pct('has_booking')*total)}/{total}", "impact": "24% more appointments"})

        avg_social = sum(len(c.get("social_platforms", []) or []) for c in accessible) / total
        if avg_social > target_trust.get("social_link_count", 0) + 1:
            gaps.append({"feature": "Social media presence", "competitors_avg": round(avg_social, 1), "you_have": target_trust.get("social_link_count", 0), "impact": "78% more customers (Social Media Examiner)"})

        return {
            "gaps_vs_competitors": [g.get("feature", str(g)) if isinstance(g, dict) else g for g in gaps],
            "competitor_feature_adoption": {k: int(pct(k) * total) for k in ["has_live_chat", "has_blog", "has_free_offer", "has_booking", "has_video"]},
            "total_competitors_analyzed": total,
        }
