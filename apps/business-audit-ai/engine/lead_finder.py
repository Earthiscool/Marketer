"""
Free lead finder based on public search result pages.

This is intentionally lightweight. It does not use paid enrichment APIs and it
does not try to bypass protected platforms. It searches DuckDuckGo HTML results,
filters out directories/social networks, and returns likely business websites
that can be audited next.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

BLOCKED_DOMAINS = {
    "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
    "facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com",
    "youtube.com", "tiktok.com", "pinterest.com",
    "yelp.com", "angi.com", "thumbtack.com", "homeadvisor.com",
    "mapquest.com", "yellowpages.com", "bbb.org", "chamberofcommerce.com",
    "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "wikipedia.org", "reddit.com", "nextdoor.com",
}


class LeadFinder:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def search(self, industry: str, location: str, limit: int = 25) -> list[dict]:
        industry = industry.strip()
        location = location.strip()
        if not industry or not location:
            return []

        queries = [
            f'{industry} "{location}" contact',
            f'{industry} "{location}" "free quote"',
            f'{industry} "{location}" "book online"',
            f'{industry} "{location}" "services"',
        ]

        seen = set()
        prospects = []
        for query in queries:
            for result in self._duckduckgo(query):
                url = self._clean_url(result.get("url", ""))
                domain = self._domain(url)
                if not url or not domain or domain in seen or self._blocked(domain):
                    continue
                seen.add(domain)
                prospects.append({
                    "business_name": self._title_to_name(result.get("title") or domain),
                    "url": url,
                    "industry": industry,
                    "location": location,
                    "source": f"DuckDuckGo: {query}",
                    "lead_score": self._pre_score(result),
                    "hook": "Run an audit to find their strongest AI lead-follow-up angle.",
                    "offer": "AI lead follow-up pilot",
                    "next_step": "Run audit",
                    "snippet": result.get("snippet", ""),
                })
                if len(prospects) >= limit:
                    return prospects
        return prospects

    def _duckduckgo(self, query: str) -> list[dict]:
        try:
            response = self.session.get(
                f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
                timeout=15,
            )
            if response.status_code != 200:
                return []
            soup = BeautifulSoup(response.text, "lxml")
            results = []
            for item in soup.select(".result"):
                link = item.select_one(".result__a")
                snippet = item.select_one(".result__snippet")
                if not link:
                    continue
                results.append({
                    "title": link.get_text(" ", strip=True),
                    "url": link.get("href", ""),
                    "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                })
            return results
        except Exception:
            return []

    def _clean_url(self, raw: str) -> str:
        if not raw:
            return ""
        if raw.startswith("//duckduckgo.com/l/"):
            parsed = urlparse("https:" + raw)
            uddg = parse_qs(parsed.query).get("uddg", [""])[0]
            raw = unquote(uddg)
        if raw.startswith("/l/?"):
            parsed = urlparse(raw)
            raw = unquote(parse_qs(parsed.query).get("uddg", [""])[0])
        if not raw.startswith("http"):
            return ""
        parsed = urlparse(raw)
        if not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower().replace("www.", "")

    def _blocked(self, domain: str) -> bool:
        if any(domain == d or domain.endswith("." + d) for d in BLOCKED_DOMAINS):
            return True
        return any(part in domain for part in ["google", "facebook", "linkedin", "yelp"])

    def _title_to_name(self, title: str) -> str:
        cleaned = re.split(r"[\|-]", title)[0].strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:80]

    def _pre_score(self, result: dict) -> int:
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        score = 45
        if "contact" in text:
            score += 8
        if "free quote" in text or "consultation" in text:
            score += 8
        if "book" in text or "appointment" in text:
            score += 6
        if "reviews" in text or "stars" in text:
            score += 4
        return min(score, 75)
