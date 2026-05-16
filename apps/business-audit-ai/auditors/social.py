"""
Social Presence Auditor — checks social media presence, activity, and engagement signals.
Uses public profile data and site-linked social accounts.
"""
import requests
import re
from typing import Optional
from datetime import datetime


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class SocialAuditor:
    def __init__(self, url: str, website_data: dict):
        self.url = url
        self.website_data = website_data

    def audit(self) -> dict:
        trust = self.website_data.get("trust_signals", {})
        social_links = trust.get("social_links_found", [])

        results = {
            "platforms_linked": [s["platform"] for s in social_links],
            "platform_urls": {s["platform"]: s["url"] for s in social_links},
            "platform_count": len(social_links),
            "missing_major_platforms": [],
            "platform_details": {},
        }

        major_platforms = ["facebook", "instagram", "linkedin", "twitter", "youtube"]
        results["missing_major_platforms"] = [p for p in major_platforms if p not in results["platforms_linked"]]

        for social in social_links:
            platform = social["platform"]
            url = social["url"]
            details = self._check_platform(platform, url)
            if details:
                results["platform_details"][platform] = details

        results["overall_assessment"] = self._assess_social(results)
        return results

    def _check_platform(self, platform: str, url: str) -> Optional[dict]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code != 200:
                return {"accessible": False, "url": url}

            html = r.text
            details = {"accessible": True, "url": url}

            if platform == "facebook":
                details.update(self._parse_facebook(html))
            elif platform == "instagram":
                details.update(self._parse_instagram(html))
            elif platform == "linkedin":
                details.update(self._parse_linkedin(html))
            elif platform == "twitter":
                details.update(self._parse_twitter(html))

            return details
        except Exception:
            return {"accessible": False, "url": url, "error": "timeout or blocked"}

    def _parse_facebook(self, html: str) -> dict:
        likes_match = re.search(r'"follower_count":(\d+)', html)
        likes = int(likes_match.group(1)) if likes_match else None

        rating_match = re.search(r'"overall_star_rating":([\d.]+)', html)
        rating = float(rating_match.group(1)) if rating_match else None

        review_match = re.search(r'"rating_count":(\d+)', html)
        reviews = int(review_match.group(1)) if review_match else None

        return {
            "followers": likes,
            "rating": rating,
            "review_count": reviews,
            "has_reviews": bool(rating),
        }

    def _parse_instagram(self, html: str) -> dict:
        follower_match = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
        followers = int(follower_match.group(1)) if follower_match else None

        post_match = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)', html)
        posts = int(post_match.group(1)) if post_match else None

        return {
            "followers": followers,
            "post_count": posts,
            "active": posts is not None and posts > 0,
        }

    def _parse_linkedin(self, html: str) -> dict:
        size_match = re.search(r'"employeeCountRange":\{"start":(\d+),"end":(\d+)\}', html)
        if size_match:
            size = f"{size_match.group(1)}-{size_match.group(2)} employees"
        else:
            size_match2 = re.search(r'(\d+[-–]\d+)\s*employees', html, re.I)
            size = size_match2.group(0) if size_match2 else None

        follower_match = re.search(r'([\d,]+)\s*followers', html, re.I)
        followers_raw = follower_match.group(1).replace(",", "") if follower_match else None
        followers = int(followers_raw) if followers_raw and followers_raw.isdigit() else None

        return {
            "company_size": size,
            "followers": followers,
            "has_company_page": True,
        }

    def _parse_twitter(self, html: str) -> dict:
        follower_match = re.search(r'"followers_count":(\d+)', html)
        followers = int(follower_match.group(1)) if follower_match else None

        tweet_match = re.search(r'"statuses_count":(\d+)', html)
        tweets = int(tweet_match.group(1)) if tweet_match else None

        return {
            "followers": followers,
            "tweet_count": tweets,
        }

    def _assess_social(self, results: dict) -> dict:
        platforms = results["platform_count"]
        missing = results["missing_major_platforms"]

        grade = "Strong" if platforms >= 3 else "Moderate" if platforms >= 1 else "Weak"

        issues = []
        if platforms == 0:
            issues.append("No social media presence found linked from website")
        if "facebook" in missing and "instagram" in missing:
            issues.append("Missing Facebook and Instagram — top platforms for local/consumer businesses")
        if "linkedin" in missing:
            issues.append("Missing LinkedIn — important for B2B credibility")
        if platforms >= 1:
            fb = results["platform_details"].get("facebook", {})
            ig = results["platform_details"].get("instagram", {})
            if fb.get("followers") and fb["followers"] < 100:
                issues.append(f"Facebook page has only {fb['followers']} followers — low social proof")
            if ig.get("post_count") and ig["post_count"] < 10:
                issues.append("Instagram shows minimal posting activity")

        return {
            "grade": grade,
            "platform_count": platforms,
            "missing_platforms": missing,
            "issues": issues,
            "primary_issue": issues[0] if issues else None,
        }
