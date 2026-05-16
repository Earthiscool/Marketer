"""
Traffic Estimator — triangulates monthly visitor estimates from multiple
public signals since SimilarWeb requires paid API access.
Uses: Google search result counts, review velocity, social following,
content volume, and industry benchmarks to produce a realistic estimate.
"""
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Industry average monthly traffic for local SMBs
INDUSTRY_TRAFFIC_BASELINES = {
    "restaurant": 2500,
    "pet store": 800,
    "plumbing": 600,
    "dental": 1200,
    "real estate": 3000,
    "law firm": 900,
    "HVAC": 700,
    "marketing agency": 2000,
    "software": 5000,
    "e-commerce": 4000,
    "fitness": 1500,
    "salon": 700,
    "medical": 1800,
    "cleaning": 500,
    "roofing": 600,
    "accounting": 800,
    "construction": 700,
    "local business": 600,
}


class TrafficAuditor:
    def __init__(self, url: str, business_name: Optional[str], business_type: str, audit_data: dict):
        self.url = url
        self.business_name = business_name
        self.business_type = business_type
        self.audit_data = audit_data

    def audit(self) -> dict:
        estimate = self._triangulate_traffic()
        sources = self._estimate_traffic_sources(estimate)
        benchmarks = self._compare_to_benchmark(estimate)

        return {
            "estimated_monthly_visitors": estimate["estimate"],
            "confidence": estimate["confidence"],
            "estimation_method": estimate["method"],
            "signals_used": estimate["signals"],
            "traffic_sources": sources,
            "benchmark_comparison": benchmarks,
            "revenue_context": self._revenue_context(estimate["estimate"]),
        }

    def _triangulate_traffic(self) -> dict:
        signals = []
        scores = []

        # Signal 1: Review count (more reviews = more customers = more traffic)
        review_count = self.audit_data.get("reviews", {}).get("assessment", {}).get("google_review_count") or 0
        if review_count > 0:
            # Industry avg: ~0.5-2% of visitors leave reviews
            review_based_estimate = review_count * 80  # ~80 visitors per review accumulated
            signals.append(f"Google reviews ({review_count}) → ~{review_based_estimate:,} cumulative visitors")
            scores.append(min(review_based_estimate / 12, 5000))  # monthly estimate

        # Signal 2: Social following
        social_data = self.audit_data.get("social", {}).get("platform_details", {})
        total_social = 0
        for platform, data in social_data.items():
            followers = data.get("followers") or 0
            total_social += followers
        if total_social > 0:
            # ~5-15% of social followers visit site monthly
            social_traffic = round(total_social * 0.08)
            signals.append(f"Social following ({total_social:,}) → ~{social_traffic:,} monthly visitors")
            scores.append(social_traffic)

        # Signal 3: SEO score proxy
        seo_score = self.audit_data.get("seo", {}).get("seo_score", {}).get("score") or 50
        baseline = INDUSTRY_TRAFFIC_BASELINES.get(self.business_type, 600)
        seo_factor = seo_score / 100
        seo_estimate = round(baseline * seo_factor)
        signals.append(f"SEO score ({seo_score}/100) × industry baseline → ~{seo_estimate:,}/month")
        scores.append(seo_estimate)

        # Signal 4: Content volume
        pages = self.audit_data.get("website", {}).get("internal_pages", {})
        page_count = len(pages) + 1
        if page_count > 5:
            page_traffic = page_count * 50
            signals.append(f"{page_count} indexed pages → ~{page_traffic:,}/month (50/page avg)")
            scores.append(page_traffic)

        # Signal 5: Try SimilarWeb public page (may be blocked)
        sw_estimate = self._try_similarweb()
        if sw_estimate:
            signals.append(f"SimilarWeb public data → ~{sw_estimate:,}/month")
            scores.append(sw_estimate)

        if not scores:
            return {
                "estimate": baseline,
                "confidence": "low",
                "method": "industry_baseline_only",
                "signals": [f"Using {self.business_type} industry baseline"],
            }

        # Weighted average, removing outliers
        scores_sorted = sorted(scores)
        if len(scores_sorted) > 2:
            scores_trimmed = scores_sorted[1:-1]  # drop highest and lowest
        else:
            scores_trimmed = scores_sorted

        estimate = round(sum(scores_trimmed) / len(scores_trimmed))
        confidence = "high" if len(scores) >= 3 else "medium" if len(scores) >= 2 else "low"

        return {
            "estimate": max(estimate, 100),
            "confidence": confidence,
            "method": "multi_signal_triangulation",
            "signals": signals,
        }

    def _try_similarweb(self) -> Optional[int]:
        try:
            domain = self.url.replace("https://", "").replace("http://", "").strip("/")
            r = requests.get(
                f"https://www.similarweb.com/website/{domain}/",
                headers=HEADERS, timeout=8
            )
            if r.status_code != 200:
                return None

            # Look for monthly visits in the page
            patterns = [
                r'"totalVisits":([\d.]+)',
                r'Total Visits[^0-9]*([0-9.,]+[KMB]?)',
                r'([0-9]+\.[0-9]+[KMB])\s*(?:Monthly Visits|visits)',
            ]
            for p in patterns:
                m = re.search(p, r.text, re.I)
                if m:
                    val = m.group(1).replace(",", "")
                    if val.endswith("K"):
                        return int(float(val[:-1]) * 1000)
                    elif val.endswith("M"):
                        return int(float(val[:-1]) * 1000000)
                    elif val.endswith("B"):
                        return int(float(val[:-1]) * 1000000000)
                    else:
                        try:
                            return int(float(val))
                        except Exception:
                            pass
        except Exception:
            pass
        return None

    def _estimate_traffic_sources(self, estimate: dict) -> dict:
        monthly = estimate["estimate"]
        seo_score = self.audit_data.get("seo", {}).get("seo_score", {}).get("score") or 50
        social_count = self.audit_data.get("social", {}).get("platform_count") or 0
        has_ads = self.audit_data.get("ads", {}).get("google_ads", {}).get("business_running_own_ad") or False

        # Estimate channel breakdown
        organic_pct = max(0.3, min(0.6, seo_score / 100))
        social_pct = min(0.2, social_count * 0.03)
        paid_pct = 0.15 if has_ads else 0
        direct_pct = max(0.1, 0.3 - social_pct - paid_pct)
        referral_pct = max(0.05, 1 - organic_pct - social_pct - paid_pct - direct_pct)

        return {
            "organic_search": {"pct": round(organic_pct * 100), "visitors": round(monthly * organic_pct)},
            "direct": {"pct": round(direct_pct * 100), "visitors": round(monthly * direct_pct)},
            "social": {"pct": round(social_pct * 100), "visitors": round(monthly * social_pct)},
            "paid": {"pct": round(paid_pct * 100), "visitors": round(monthly * paid_pct)},
            "referral": {"pct": round(referral_pct * 100), "visitors": round(monthly * referral_pct)},
        }

    def _compare_to_benchmark(self, estimate: dict) -> dict:
        monthly = estimate["estimate"]
        baseline = INDUSTRY_TRAFFIC_BASELINES.get(self.business_type, 600)
        pct_of_baseline = round((monthly / baseline) * 100)

        return {
            "industry_baseline": baseline,
            "your_estimate": monthly,
            "vs_baseline_pct": pct_of_baseline,
            "assessment": "Above average" if pct_of_baseline > 120 else
                          "Average" if pct_of_baseline > 80 else
                          "Below average" if pct_of_baseline > 40 else "Significantly below average",
            "gap_to_top_performer": max(0, baseline * 3 - monthly),
        }

    def _revenue_context(self, monthly_visitors: int) -> dict:
        avg_conversion = 0.025
        estimated_leads = round(monthly_visitors * avg_conversion)

        return {
            "estimated_monthly_leads": estimated_leads,
            "note": "Based on 2.35% industry avg conversion rate",
            "with_optimized_funnel": round(monthly_visitors * 0.06),
            "traffic_is_the_bottleneck": monthly_visitors < 500,
            "conversion_is_the_bottleneck": monthly_visitors >= 500 and estimated_leads < 20,
        }
