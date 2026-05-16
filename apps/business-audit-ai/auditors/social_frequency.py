"""
Social Posting Frequency Auditor — finds WHEN a business last posted on each platform.
social.py already captures follower counts; this adds the temporal dimension.

A business with 3,000 Instagram followers but last post 4 months ago
is a perfect cold email hook: "You're paying for an audience you're not talking to."

Approach: fetch public pages, extract post timestamps from embedded JSON or datetime attrs.
Degrades gracefully — returns "inactive" signal even when exact dates aren't parseable.
"""
import re
import time
import random
import requests
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

ACTIVITY_LEVELS = {
    "active":   (0, 7,   "Active — posting within the last week"),
    "moderate": (7, 30,  "Moderate — last post was 1-4 weeks ago"),
    "stale":    (30, 90, "Stale — no post in 1-3 months"),
    "inactive": (90, 365,"Inactive — no post in 3-12 months"),
    "dormant":  (365, 99999, "Dormant — no post in over a year"),
}


def _activity_level(days: Optional[int]) -> str:
    if days is None:
        return "unknown"
    for label, (lo, hi, _) in ACTIVITY_LEVELS.items():
        if lo <= days < hi:
            return label
    return "dormant"


def _days_ago(ts: int) -> int:
    now = datetime.now(timezone.utc).timestamp()
    return int((now - ts) / 86400)


class SocialFrequencyAuditor:
    def __init__(self, url: str, website_data: dict):
        self.url = url
        self.website_data = website_data

    def audit(self) -> dict:
        trust = self.website_data.get("trust_signals", {})
        social_links = trust.get("social_links_found", [])
        platform_urls = {s["platform"]: s["url"] for s in social_links}

        results = {}
        for platform, social_url in platform_urls.items():
            time.sleep(random.uniform(0.4, 0.9))
            result = self._check_platform(platform, social_url)
            if result:
                results[platform] = result

        # Identify platforms that are stale/inactive
        stale = [p for p, d in results.items() if d.get("activity_level") in ("stale", "inactive", "dormant")]
        active = [p for p, d in results.items() if d.get("activity_level") in ("active", "moderate")]
        no_data = [p for p, d in results.items() if d.get("activity_level") == "unknown"]

        cold_email_angle = self._cold_email_angle(results, stale, platform_urls)

        return {
            "platforms_checked": list(results.keys()),
            "platform_frequency": results,
            "stale_platforms": stale,
            "active_platforms": active,
            "unknown_platforms": no_data,
            "total_platforms": len(results),
            "worst_platform": self._worst_platform(results),
            "cold_email_angle": cold_email_angle,
        }

    def _check_platform(self, platform: str, url: str) -> Optional[dict]:
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            html = r.text

            if platform == "facebook":
                return self._parse_facebook_frequency(html, url)
            elif platform == "instagram":
                return self._parse_instagram_frequency(html, url)
            elif platform == "linkedin":
                return self._parse_linkedin_frequency(html, url)
            elif platform == "twitter":
                return self._parse_twitter_frequency(html, url)
            elif platform == "youtube":
                return self._parse_youtube_frequency(html, url)
            else:
                return self._parse_generic_frequency(html, url, platform)
        except Exception:
            return {"url": url, "activity_level": "unknown", "error": "fetch failed"}

    def _parse_facebook_frequency(self, html: str, url: str) -> dict:
        days = None

        # Facebook embeds Unix timestamps in multiple places
        # Pattern 1: "creation_time":1735000000
        timestamps = re.findall(r'"creation_time"\s*:\s*(\d{10})', html)
        if not timestamps:
            # Pattern 2: "published_time":1735000000
            timestamps = re.findall(r'"published_time"\s*:\s*(\d{10})', html)
        if not timestamps:
            # Pattern 3: data-utime attribute
            timestamps = re.findall(r'data-utime="(\d{10})"', html)
        if not timestamps:
            # Pattern 4: datetime attribute on <abbr> or <time>
            soup = BeautifulSoup(html, "lxml")
            time_tags = soup.find_all(["abbr", "time"], attrs={"data-utime": True})
            timestamps = [t["data-utime"] for t in time_tags if t.get("data-utime")]

        if timestamps:
            # Get the most recent timestamp
            ts_ints = sorted([int(t) for t in timestamps if len(t) == 10], reverse=True)
            if ts_ints:
                days = _days_ago(ts_ints[0])
                last_post_date = datetime.fromtimestamp(ts_ints[0]).strftime("%Y-%m-%d")
                return {
                    "url": url,
                    "days_since_last_post": days,
                    "last_post_date": last_post_date,
                    "activity_level": _activity_level(days),
                    "posts_found": len(ts_ints),
                }

        # Fallback: check for recency language in the HTML
        activity = self._infer_from_text(html)
        return {"url": url, "days_since_last_post": activity, "activity_level": _activity_level(activity), "data_source": "text_inference"}

    def _parse_instagram_frequency(self, html: str, url: str) -> dict:
        days = None

        # Instagram embeds timestamps in JSON
        # Pattern 1: "taken_at_timestamp":1735000000
        timestamps = re.findall(r'"taken_at_timestamp"\s*:\s*(\d{10})', html)
        if not timestamps:
            # Pattern 2: "taken_at":1735000000
            timestamps = re.findall(r'"taken_at"\s*:\s*(\d{10})', html)
        if not timestamps:
            # Pattern 3: datetime in meta tags
            soup = BeautifulSoup(html, "lxml")
            date_meta = soup.find("meta", {"property": "article:published_time"})
            if date_meta:
                try:
                    dt = datetime.fromisoformat(date_meta["content"].replace("Z", "+00:00"))
                    days = (datetime.now(timezone.utc) - dt).days
                    return {
                        "url": url,
                        "days_since_last_post": days,
                        "last_post_date": dt.strftime("%Y-%m-%d"),
                        "activity_level": _activity_level(days),
                    }
                except Exception:
                    pass

        if timestamps:
            ts_ints = sorted([int(t) for t in timestamps if len(t) == 10], reverse=True)
            if ts_ints:
                days = _days_ago(ts_ints[0])
                last_post_date = datetime.fromtimestamp(ts_ints[0]).strftime("%Y-%m-%d")
                return {
                    "url": url,
                    "days_since_last_post": days,
                    "last_post_date": last_post_date,
                    "activity_level": _activity_level(days),
                    "posts_found": len(ts_ints),
                }

        # Instagram increasingly blocks scrapers — check if page loaded at all
        if "Page Not Found" in html or "This page isn't available" in html:
            return {"url": url, "activity_level": "unknown", "note": "account not found or private"}
        if len(html) < 2000:
            return {"url": url, "activity_level": "unknown", "note": "blocked or login required"}

        # Page loaded but can't extract timestamps
        post_count_match = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)', html)
        post_count = int(post_count_match.group(1)) if post_count_match else None

        return {
            "url": url,
            "post_count": post_count,
            "activity_level": "active" if post_count and post_count > 0 else "unknown",
            "note": "timestamp extraction unavailable — Instagram restricted access",
        }

    def _parse_linkedin_frequency(self, html: str, url: str) -> dict:
        # LinkedIn requires login for most content — check what's visible
        if "authwall" in html.lower() or "join linkedin" in html.lower() or len(html) < 3000:
            return {"url": url, "activity_level": "unknown", "note": "LinkedIn requires login to view posts"}

        # Try to extract update timestamps from public company pages
        timestamps = re.findall(r'"postedAt"\s*:\s*(\d{13})', html)  # ms timestamps
        if timestamps:
            ts_ints = sorted([int(t) // 1000 for t in timestamps], reverse=True)
            days = _days_ago(ts_ints[0])
            return {
                "url": url,
                "days_since_last_post": days,
                "last_post_date": datetime.fromtimestamp(ts_ints[0]).strftime("%Y-%m-%d"),
                "activity_level": _activity_level(days),
                "posts_found": len(ts_ints),
            }

        # Follower count as proxy
        follower_match = re.search(r'([\d,]+)\s*followers', html, re.I)
        followers = int(follower_match.group(1).replace(",", "")) if follower_match else None

        return {
            "url": url,
            "followers": followers,
            "activity_level": "unknown",
            "note": "LinkedIn post dates not publicly accessible without login",
        }

    def _parse_twitter_frequency(self, html: str, url: str) -> dict:
        # Twitter/X now requires login to view most content
        if "log in" in html.lower() or len(html) < 5000:
            return {"url": url, "activity_level": "unknown", "note": "X/Twitter requires login to view posts"}

        # Some timestamp patterns from older cached versions
        timestamps = re.findall(r'"created_at"\s*:\s*"([^"]+)"', html)
        if timestamps:
            try:
                dt = datetime.strptime(timestamps[0], "%a %b %d %H:%M:%S +0000 %Y")
                days = (datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).days
                return {
                    "url": url,
                    "days_since_last_post": days,
                    "last_post_date": dt.strftime("%Y-%m-%d"),
                    "activity_level": _activity_level(days),
                }
            except Exception:
                pass

        return {"url": url, "activity_level": "unknown", "note": "X/Twitter requires login to view posts"}

    def _parse_youtube_frequency(self, html: str, url: str) -> dict:
        # YouTube embeds upload dates in schema/JSON
        timestamps = re.findall(r'"dateText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"', html)
        if not timestamps:
            # ISO date pattern in JSON
            dates = re.findall(r'"publishDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
            if dates:
                try:
                    dt = datetime.strptime(max(dates), "%Y-%m-%d")
                    days = (datetime.now() - dt).days
                    return {
                        "url": url,
                        "days_since_last_post": days,
                        "last_post_date": max(dates),
                        "activity_level": _activity_level(days),
                    }
                except Exception:
                    pass

        # Check subscriber count as engagement proxy
        sub_match = re.search(r'"subscriberCountText".*?"simpleText"\s*:\s*"([^"]+)"', html)
        subs = sub_match.group(1) if sub_match else None

        return {
            "url": url,
            "subscribers": subs,
            "activity_level": "unknown",
            "note": "Could not extract upload dates",
        }

    def _parse_generic_frequency(self, html: str, url: str, platform: str) -> dict:
        days = self._infer_from_text(html)
        return {
            "url": url,
            "days_since_last_post": days,
            "activity_level": _activity_level(days),
            "platform": platform,
        }

    def _infer_from_text(self, html: str) -> Optional[int]:
        """Scan for relative time phrases like '2 hours ago', '3 days ago'."""
        patterns = [
            (r'(\d+)\s+minute[s]?\s+ago', lambda m: 0),
            (r'(\d+)\s+hour[s]?\s+ago',   lambda m: 0),
            (r'(\d+)\s+day[s]?\s+ago',    lambda m: int(m.group(1))),
            (r'(\d+)\s+week[s]?\s+ago',   lambda m: int(m.group(1)) * 7),
            (r'(\d+)\s+month[s]?\s+ago',  lambda m: int(m.group(1)) * 30),
            (r'(\d+)\s+year[s]?\s+ago',   lambda m: int(m.group(1)) * 365),
        ]
        for pattern, calc in patterns:
            m = re.search(pattern, html, re.I)
            if m:
                return calc(m)
        return None

    def _worst_platform(self, results: dict) -> Optional[dict]:
        """Return the platform with the most stale/inactive posting."""
        worst = None
        worst_days = -1
        for platform, data in results.items():
            days = data.get("days_since_last_post")
            if days and days > worst_days:
                worst_days = days
                worst = {"platform": platform, "days_since_last_post": days, "activity_level": data.get("activity_level")}
        return worst

    def _cold_email_angle(self, results: dict, stale: list, platform_urls: dict) -> Optional[str]:
        if not stale:
            return None

        # Find worst offender with known days
        worst_days = 0
        worst_platform = None
        for p in stale:
            days = results.get(p, {}).get("days_since_last_post", 0) or 0
            if days > worst_days:
                worst_days = days
                worst_platform = p

        followers = None
        if worst_platform:
            # Try to get follower count from platform data
            followers = results.get(worst_platform, {}).get("followers")

        if worst_platform and worst_days > 0:
            months = round(worst_days / 30, 1)
            if followers:
                return (
                    f"Your {worst_platform.capitalize()} page has {followers:,} followers "
                    f"but you haven't posted in {months:.0f} months — you're paying for an audience you're not talking to."
                )
            return (
                f"Your {worst_platform.capitalize()} account hasn't posted in ~{months:.0f} months "
                f"while your competitors are posting weekly — you're invisible on social right now."
            )

        if stale:
            platforms_str = " and ".join(p.capitalize() for p in stale[:2])
            return f"Your {platforms_str} presence appears inactive — competitors are staying top-of-mind while you're silent."

        return None
