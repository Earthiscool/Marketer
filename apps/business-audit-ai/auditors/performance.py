"""
Performance Auditor — uses Google PageSpeed Insights API when available,
falls back to direct HTTP measurement when rate-limited.
"""
import requests
import time
import os
import re
from typing import Optional
from bs4 import BeautifulSoup


PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class PerformanceAuditor:
    def __init__(self, url: str):
        self.url = url
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def audit(self) -> dict:
        mobile = self._fetch_pagespeed("mobile")
        desktop = self._fetch_pagespeed("desktop")

        mobile_failed = mobile is None or (isinstance(mobile, dict) and mobile.get("error"))
        desktop_failed = desktop is None or (isinstance(desktop, dict) and desktop.get("error"))

        if mobile_failed or desktop_failed:
            # API unavailable — fall back to direct measurement
            return self._direct_measurement_audit()

        return {
            "mobile": self._parse_result(mobile, "mobile"),
            "desktop": self._parse_result(desktop, "desktop"),
            "summary": self._summarize(mobile, desktop),
            "source": "pagespeed_api",
        }

    def _fetch_pagespeed(self, strategy: str) -> Optional[dict]:
        try:
            params = {
                "url": self.url,
                "strategy": strategy,
                "category": ["performance", "seo", "accessibility", "best-practices"],
            }
            if self.api_key:
                params["key"] = self.api_key

            r = requests.get(PAGESPEED_API, params=params, timeout=30)
            # Guard against non-JSON responses (HTML error pages, etc.)
            content_type = r.headers.get("Content-Type", "")
            if "json" not in content_type and r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            try:
                data = r.json()
            except Exception:
                return {"error": "non-JSON response from PageSpeed API"}
            if r.status_code == 429 or "error" in data:
                return {"error": data.get("error", {}).get("message", "rate limited")}
            if r.status_code == 200:
                return data
        except Exception:
            pass
        return None

    def _direct_measurement_audit(self) -> dict:
        """Measure performance directly by timing HTTP requests and analyzing HTML."""
        results = {"source": "direct_measurement", "api_note": "PageSpeed API rate-limited — using direct HTTP measurement"}

        # Measure load time
        mobile_time = self._measure_load_time(mobile=True)
        desktop_time = self._measure_load_time(mobile=False)

        # Analyze HTML for performance signals
        try:
            start = time.time()
            r = requests.get(self.url, headers=HEADERS, timeout=15)
            ttfb = time.time() - start
            html = r.text
            soup = BeautifulSoup(html, "lxml")
            content_size_kb = len(html.encode("utf-8")) / 1024
        except Exception:
            html = ""
            soup = None
            ttfb = None
            content_size_kb = None

        signals = self._analyze_html_performance(soup, html) if soup else {}

        mobile_score = self._estimate_score(mobile_time, signals)
        desktop_score = self._estimate_score(desktop_time, signals)

        visitor_loss = self._estimate_visitor_loss(mobile_time)

        results["mobile"] = {
            "strategy": "mobile",
            "measured_load_time_seconds": mobile_time,
            "estimated_score": mobile_score,
            "grade": self._grade(mobile_score),
            "ttfb_seconds": round(ttfb, 3) if ttfb else None,
        }
        results["desktop"] = {
            "strategy": "desktop",
            "measured_load_time_seconds": desktop_time,
            "estimated_score": desktop_score,
            "grade": self._grade(desktop_score),
        }
        results["signals"] = signals
        results["summary"] = {
            "mobile_performance_score": mobile_score,
            "desktop_performance_score": desktop_score,
            "estimated_lcp_seconds": mobile_time,
            "mobile_grade": self._grade(mobile_score),
            "desktop_grade": self._grade(desktop_score),
            "visitor_loss_estimate": visitor_loss,
            "page_size_kb": round(content_size_kb, 1) if content_size_kb else None,
            "ttfb_seconds": round(ttfb, 3) if ttfb else None,
        }

        return results

    def _measure_load_time(self, mobile: bool = True) -> Optional[float]:
        ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
              if mobile else HEADERS["User-Agent"])
        try:
            start = time.time()
            r = requests.get(self.url, headers={"User-Agent": ua}, timeout=15)
            elapsed = time.time() - start
            return round(elapsed, 2)
        except Exception:
            return None

    def _analyze_html_performance(self, soup: BeautifulSoup, html: str) -> dict:
        images = soup.find_all("img")
        lazy_images = [i for i in images if i.get("loading") == "lazy"]
        unoptimized_images = [i for i in images if not i.get("loading") and not i.get("width")]

        scripts = soup.find_all("script", src=True)
        render_blocking = [s for s in scripts if not s.get("async") and not s.get("defer")]

        css_links = soup.find_all("link", {"rel": "stylesheet"})
        has_minified_css = any(".min.css" in (l.get("href") or "") for l in css_links)

        inline_styles = len(soup.find_all("style"))
        has_webp = "webp" in html.lower()
        has_preload = bool(soup.find("link", {"rel": "preload"}))
        has_lazy_load = bool(lazy_images)
        has_gzip = False  # Can't detect without response headers easily

        html_size_kb = len(html.encode()) / 1024
        render_blocking_count = len(render_blocking)
        unoptimized_img_count = len(unoptimized_images)

        issues = []
        if render_blocking_count > 2:
            issues.append(f"{render_blocking_count} render-blocking scripts (no async/defer)")
        if unoptimized_img_count > 3:
            issues.append(f"{unoptimized_img_count} images missing lazy loading / size attributes")
        if html_size_kb > 200:
            issues.append(f"Large HTML document ({html_size_kb:.0f}KB)")
        if not has_preload:
            issues.append("No resource preloading detected")

        return {
            "render_blocking_scripts": render_blocking_count,
            "images_missing_lazy_load": unoptimized_img_count,
            "has_webp_images": has_webp,
            "has_preload_hints": has_preload,
            "has_lazy_loading": has_lazy_load,
            "has_minified_css": has_minified_css,
            "html_size_kb": round(html_size_kb, 1),
            "inline_style_blocks": inline_styles,
            "issues_detected": issues,
        }

    def _estimate_score(self, load_time: Optional[float], signals: dict) -> int:
        if load_time is None:
            # Can't measure load time — estimate from HTML signals alone
            score = 55
            if signals.get("render_blocking_scripts", 0) > 3:
                score -= 15
            if signals.get("images_missing_lazy_load", 0) > 5:
                score -= 10
            if signals.get("has_webp_images"):
                score += 5
            if signals.get("has_preload_hints"):
                score += 3
            return max(10, min(100, score))
        # Base score from load time
        if load_time < 1.0:
            score = 95
        elif load_time < 2.5:
            score = 80
        elif load_time < 4.0:
            score = 60
        elif load_time < 6.0:
            score = 40
        else:
            score = 20

        # Adjust for signals
        if signals.get("render_blocking_scripts", 0) > 3:
            score -= 10
        if signals.get("images_missing_lazy_load", 0) > 5:
            score -= 8
        if signals.get("has_webp_images"):
            score += 5
        if signals.get("has_preload_hints"):
            score += 3

        return max(0, min(100, score))

    def _parse_result(self, data: dict, strategy: str) -> dict:
        if not data or data.get("error"):
            return {"error": data.get("error") if data else "no data"}

        categories = data.get("lighthouseResult", {}).get("categories", {})
        audits = data.get("lighthouseResult", {}).get("audits", {})

        scores = {
            "performance_score": self._score(categories.get("performance", {})),
            "seo_score": self._score(categories.get("seo", {})),
            "accessibility_score": self._score(categories.get("accessibility", {})),
            "best_practices_score": self._score(categories.get("best-practices", {})),
        }

        core_web_vitals = {
            "first_contentful_paint": self._audit_value(audits, "first-contentful-paint"),
            "largest_contentful_paint": self._audit_value(audits, "largest-contentful-paint"),
            "total_blocking_time": self._audit_value(audits, "total-blocking-time"),
            "cumulative_layout_shift": self._audit_value(audits, "cumulative-layout-shift"),
            "speed_index": self._audit_value(audits, "speed-index"),
            "interactive": self._audit_value(audits, "interactive"),
        }

        return {
            "strategy": strategy,
            "scores": scores,
            "core_web_vitals": core_web_vitals,
            "top_opportunities": self._extract_top_issues(audits),
        }

    def _score(self, category: dict) -> Optional[int]:
        score = category.get("score")
        return int(score * 100) if score is not None else None

    def _audit_value(self, audits: dict, key: str) -> Optional[dict]:
        audit = audits.get(key, {})
        if not audit:
            return None
        return {
            "display_value": audit.get("displayValue"),
            "score": audit.get("score"),
            "numeric_value": audit.get("numericValue"),
        }

    def _extract_top_issues(self, audits: dict) -> list:
        issues = []
        keys = ["render-blocking-resources", "unused-css-rules", "unused-javascript",
                "uses-optimized-images", "uses-webp-images", "uses-text-compression"]
        for key in keys:
            audit = audits.get(key, {})
            if audit and audit.get("score") is not None and audit.get("score") < 0.9:
                issues.append({
                    "id": key,
                    "title": audit.get("title"),
                    "score": audit.get("score"),
                    "display_value": audit.get("displayValue"),
                })
        return issues[:5]

    def _summarize(self, mobile: Optional[dict], desktop: Optional[dict]) -> dict:
        mobile_perf = None
        desktop_perf = None
        lcp_ms = None

        if mobile and not mobile.get("error"):
            cats = mobile.get("lighthouseResult", {}).get("categories", {})
            perf = cats.get("performance", {}).get("score")
            mobile_perf = int(perf * 100) if perf else None
            lcp = mobile.get("lighthouseResult", {}).get("audits", {}).get("largest-contentful-paint", {})
            lcp_ms = lcp.get("numericValue")

        if desktop and not desktop.get("error"):
            cats = desktop.get("lighthouseResult", {}).get("categories", {})
            perf = cats.get("performance", {}).get("score")
            desktop_perf = int(perf * 100) if perf else None

        load_time = round(lcp_ms / 1000, 2) if lcp_ms else None

        return {
            "mobile_performance_score": mobile_perf,
            "desktop_performance_score": desktop_perf,
            "estimated_lcp_seconds": load_time,
            "mobile_grade": self._grade(mobile_perf),
            "desktop_grade": self._grade(desktop_perf),
            "visitor_loss_estimate": self._estimate_visitor_loss(load_time),
        }

    def _grade(self, score: Optional[int]) -> str:
        if score is None:
            return "unknown"
        if score >= 90:
            return "Good"
        elif score >= 50:
            return "Needs Improvement"
        else:
            return "Poor"

    def _estimate_visitor_loss(self, load_time: Optional[float]) -> Optional[str]:
        if load_time is None:
            return None
        if load_time <= 1:
            return "Minimal loss — fast site"
        elif load_time <= 3:
            loss = round((load_time - 1) * 7)
            return f"~{loss}% conversion loss from page speed delay"
        else:
            loss = min(round(53 + (load_time - 3) * 10), 90)
            return f"~{loss}% of mobile visitors likely abandoning before page loads (Google: 53% leave at 3s+)"
