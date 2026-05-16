"""
Reviews Auditor — analyzes business reviews and online reputation signals.
Checks Google Business presence, review velocity, sentiment patterns, and response behavior.
"""
import requests
import re
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import quote_plus


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class ReviewAuditor:
    def __init__(self, url: str, business_name: Optional[str], website_data: dict):
        self.url = url
        self.business_name = business_name
        self.website_data = website_data

    def audit(self) -> dict:
        trust = self.website_data.get("trust_signals", {})
        homepage = self.website_data.get("homepage", {})

        on_site_reviews = self._analyze_on_site_reviews(homepage)
        google_data = self._search_google_reviews()
        reputation_signals = self._reputation_signals(trust, on_site_reviews, google_data)

        return {
            "on_site_reviews": on_site_reviews,
            "google_business": google_data,
            "reputation_signals": reputation_signals,
            "assessment": self._assess_reviews(on_site_reviews, google_data, reputation_signals),
        }

    def _analyze_on_site_reviews(self, homepage: dict) -> dict:
        testimonials = homepage.get("has_testimonials", {})
        trust = self.website_data.get("trust_signals", {})

        return {
            "has_testimonials_section": testimonials.get("has_testimonials", False),
            "testimonial_count": testimonials.get("quote_count", 0),
            "has_star_ratings": testimonials.get("star_rating_elements", 0) > 0,
            "has_google_reviews_widget": trust.get("has_google_reviews_widget", False),
            "review_indicators_found": testimonials.get("indicators_found", []),
            "has_case_studies": trust.get("has_case_studies", False),
            "reviews_show_social_proof": testimonials.get("has_testimonials", False) or
                                          trust.get("has_case_studies", False),
        }

    def _search_google_reviews(self) -> dict:
        if not self.business_name:
            return self._try_extract_from_search()
        return self._try_extract_from_search(self.business_name)

    def _try_extract_from_search(self, business_name: Optional[str] = None) -> dict:
        try:
            query = business_name if business_name else self.url
            # Use local search results which surface the GMB panel
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=lcl"

            r = requests.get(search_url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                return {"error": "Could not access search results"}

            html = r.text
            rating = None
            review_count = None

            # aria-label="Rated 4.8 out of 5, 300 user reviews"
            aria_match = re.search(
                r'aria-label="Rated\s+([\d.]+)\s+out of\s+\d+,\s*([\d,]+)\s+user reviews?"',
                html, re.I
            )
            if aria_match:
                rating = float(aria_match.group(1))
                review_count = int(aria_match.group(2).replace(",", ""))

            # Fallback: rating value in span + separate review count
            if not rating:
                rating_span = re.search(r'class="yi40Hd[^"]*"[^>]*>([\d.]+)<', html)
                if rating_span:
                    rating = float(rating_span.group(1))

            if not review_count:
                review_match = re.search(r'([\d,]+)\s+(?:user\s+)?reviews?', html, re.I)
                if review_match:
                    review_count = int(review_match.group(1).replace(",", ""))

            # Second fallback: regular search page
            if not rating:
                search_url2 = f"https://www.google.com/search?q={quote_plus(query + ' reviews')}"
                r2 = requests.get(search_url2, headers=HEADERS, timeout=10)
                html2 = r2.text
                aria2 = re.search(
                    r'aria-label="Rated\s+([\d.]+)\s+out of\s+\d+,\s*([\d,]+)\s+(?:user\s+)?reviews?"',
                    html2, re.I
                )
                if aria2:
                    rating = float(aria2.group(1))
                    review_count = int(aria2.group(2).replace(",", ""))

            has_gmb = rating is not None

            return {
                "found_in_search": has_gmb,
                "average_rating": rating,
                "review_count": review_count,
                "rating_grade": self._grade_rating(rating, review_count),
                "review_velocity_issue": review_count is not None and review_count < 10,
                "low_review_count": review_count is not None and review_count < 25,
            }
        except Exception as e:
            return {"error": str(e), "found_in_search": False}

    def _grade_rating(self, rating: Optional[float], count: Optional[int]) -> Optional[str]:
        if rating is None:
            return None
        if rating >= 4.5 and count and count >= 50:
            return "Excellent"
        elif rating >= 4.0 and count and count >= 20:
            return "Good"
        elif rating >= 3.5:
            return "Below Average"
        else:
            return "Poor"

    def _reputation_signals(self, trust: dict, on_site: dict, google: dict) -> dict:
        issues = []

        review_count = google.get("review_count")
        rating = google.get("average_rating")

        if review_count is not None:
            if review_count < 10:
                issues.append({
                    "severity": "critical",
                    "finding": f"Only {review_count} Google reviews",
                    "benchmark": "Businesses with 50+ reviews get 4.6x more clicks than those with <10",
                    "impact": f"Missing ~{min(int((50 - review_count) * 2.3), 200)} potential monthly inquiries from review visibility",
                })
            elif review_count < 25:
                issues.append({
                    "severity": "high",
                    "finding": f"{review_count} Google reviews — below competitive threshold",
                    "benchmark": "Local businesses average 39 reviews. Top performers have 100+",
                    "impact": "Ranking lower in Google Maps 3-pack than competitors with more reviews",
                })

        if rating is not None and rating < 4.0:
            issues.append({
                "severity": "critical",
                "finding": f"{rating}/5 average rating",
                "benchmark": "93% of consumers say online reviews influence purchase decisions. 94% avoid businesses with <4.0 rating",
                "impact": "Majority of potential customers seeing your rating are choosing competitors",
            })

        if not on_site.get("has_testimonials_section"):
            issues.append({
                "severity": "medium",
                "finding": "No testimonials or social proof visible on homepage",
                "benchmark": "Landing pages with testimonials convert 34% higher than those without",
                "impact": "Visitors have no social proof to build trust before contacting you",
            })

        if not on_site.get("has_google_reviews_widget") and review_count and review_count >= 10:
            issues.append({
                "severity": "medium",
                "finding": "Google reviews not embedded on website",
                "benchmark": "Displaying reviews on-site increases conversion by up to 270%",
                "impact": "Leaving conversion trust signals off the page where decisions are made",
            })

        return {
            "issues_found": issues,
            "issue_count": len(issues),
            "has_critical_issues": any(i["severity"] == "critical" for i in issues),
        }

    def _assess_reviews(self, on_site: dict, google: dict, reputation: dict) -> dict:
        review_count = google.get("review_count", 0) or 0
        rating = google.get("average_rating")

        grade = "Unknown"
        if rating and review_count:
            if rating >= 4.5 and review_count >= 50:
                grade = "Strong"
            elif rating >= 4.0 and review_count >= 20:
                grade = "Moderate"
            else:
                grade = "Weak"
        elif review_count == 0:
            grade = "Critical"

        primary_issue = reputation["issues_found"][0] if reputation["issues_found"] else None

        return {
            "grade": grade,
            "google_rating": rating,
            "google_review_count": review_count,
            "on_site_social_proof": on_site.get("reviews_show_social_proof", False),
            "primary_issue": primary_issue,
            "total_issues": reputation["issue_count"],
        }
