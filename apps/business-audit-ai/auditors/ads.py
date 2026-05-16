"""
Ad Intelligence — checks Facebook Ad Library for business ad activity.
Reveals if they're running ads, how long, how many, what types.
Also checks for Google Ads presence via search results.
"""
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class AdsAuditor:
    def __init__(self, url: str, business_name: Optional[str], website_data: dict):
        self.url = url
        self.business_name = business_name
        self.website_data = website_data

    def audit(self) -> dict:
        fb_ads = self._check_facebook_ads()
        google_ads = self._check_google_ads()
        pixel_data = self._check_tracking_pixels()
        ad_strategy = self._assess_ad_strategy(fb_ads, google_ads, pixel_data)

        return {
            "facebook_ads": fb_ads,
            "google_ads": google_ads,
            "tracking_pixels": pixel_data,
            "ad_strategy_assessment": ad_strategy,
        }

    def _check_facebook_ads(self) -> dict:
        if not self.business_name:
            return {"checked": False, "reason": "No business name provided"}

        try:
            search_term = quote_plus(self.business_name)
            lib_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q={search_term}&search_type=keyword_unordered"

            r = requests.get(lib_url, headers=HEADERS, timeout=10)
            html = r.text

            no_ads_signals = [
                "no ads match",
                "no results",
                "0 results",
                '"totalCount":0',
                "There are no ads",
            ]
            is_running_ads = not any(s.lower() in html.lower() for s in no_ads_signals)

            ad_count_match = re.search(r'"totalCount":(\d+)', html)
            ad_count = int(ad_count_match.group(1)) if ad_count_match else None

            active_match = re.search(r'"activeAdCount":(\d+)', html)
            active_count = int(active_match.group(1)) if active_match else None

            return {
                "checked": True,
                "library_url": lib_url,
                "appears_to_run_ads": is_running_ads and (ad_count is None or ad_count > 0),
                "estimated_ad_count": ad_count,
                "active_ads": active_count,
                "note": "Check library URL manually for full creative details",
            }
        except Exception as e:
            return {"checked": False, "error": str(e)}

    def _check_google_ads(self) -> dict:
        if not self.business_name:
            return {"checked": False}

        try:
            query = self.business_name
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            r = requests.get(search_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "lxml")
            html = r.text

            sponsored_indicators = [
                "data-text-ad",
                "Sponsored",
                "aria-label=\"Ad\"",
                "class=\"uEierd\"",
                "data-hveid",
            ]
            running_google_ads = any(ind in html for ind in sponsored_indicators)

            own_ad_in_results = False
            domain = self.url.replace("https://", "").replace("http://", "").split("/")[0]
            if running_google_ads:
                own_ad_in_results = domain in html[:html.find("Sponsored") + 2000] if "Sponsored" in html else False

            return {
                "checked": True,
                "google_ads_visible_in_search": running_google_ads,
                "business_running_own_ad": own_ad_in_results,
                "competitors_running_ads_on_name": running_google_ads and not own_ad_in_results,
                "risk": "Competitors are bidding on your brand name and stealing your traffic" if running_google_ads and not own_ad_in_results else None,
            }
        except Exception as e:
            return {"checked": False, "error": str(e)}

    def _check_tracking_pixels(self) -> dict:
        tech = self.website_data.get("technical_signals", {})
        analytics = tech.get("analytics_installed", {})

        has_pixel = analytics.get("facebook_pixel", False)
        has_ga = analytics.get("google_analytics", False)
        has_gtm = analytics.get("google_tag_manager", False)

        missing = []
        if not has_pixel:
            missing.append("Facebook Pixel — can't run retargeting ads or build lookalike audiences")
        if not has_ga:
            missing.append("Google Analytics — no visibility into traffic sources or behavior")
        if not has_gtm:
            missing.append("Google Tag Manager — harder to deploy new tracking without developer")

        return {
            "has_facebook_pixel": has_pixel,
            "has_google_analytics": has_ga,
            "has_tag_manager": has_gtm,
            "missing_tracking": missing,
            "retargeting_capable": has_pixel,
            "blind_to_traffic": not has_ga,
            "impact": "Without Facebook Pixel, 70% of potential retargeting revenue is unreachable (WordStream)" if not has_pixel else None,
        }

    def _assess_ad_strategy(self, fb: dict, google: dict, pixels: dict) -> dict:
        issues = []

        if not fb.get("appears_to_run_ads") and not google.get("business_running_own_ad"):
            issues.append({
                "finding": "No paid advertising detected",
                "impact": "Relying 100% on organic — no guaranteed traffic pipeline",
                "benchmark": "Businesses using paid ads grow revenue 2.3x faster than organic-only (Google Economic Impact)",
            })

        if google.get("competitors_running_ads_on_name"):
            issues.append({
                "finding": "Competitors are running Google Ads on your brand name",
                "impact": "Customers searching specifically for you are being intercepted by competitors",
                "benchmark": "Brand keyword campaigns have avg 5-10x ROI — cheapest clicks you can buy",
            })

        if not pixels.get("retargeting_capable"):
            issues.append({
                "finding": "No Facebook Pixel installed — retargeting not possible",
                "impact": "Only 2% of visitors convert on first visit. Without retargeting, the other 98% are gone forever.",
                "benchmark": "Retargeted ads are 70% more likely to convert than cold traffic (Criteo)",
            })

        if pixels.get("blind_to_traffic"):
            issues.append({
                "finding": "No Google Analytics — operating blind",
                "impact": "Can't identify which marketing channels bring customers, can't optimize spend",
                "benchmark": "Businesses using analytics are 1.5x more likely to make better decisions and grow faster",
            })

        return {
            "issues": issues,
            "ad_maturity": "None" if len(issues) >= 3 else "Basic" if len(issues) >= 1 else "Established",
            "most_urgent": issues[0] if issues else None,
        }
