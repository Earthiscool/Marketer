"""
Wayback Machine Auditor — checks archive.org for site history.
Reveals: last redesign, how often they update, if they're growing or shrinking,
what pages they've added/removed, trajectory signals.
"""
import requests
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


class WaybackAuditor:
    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc

    def audit(self) -> dict:
        availability = self._check_availability()
        history = self._get_snapshot_history()
        changes = self._analyze_changes(history)

        return {
            "has_archive": availability.get("available", False),
            "oldest_snapshot": availability.get("oldest"),
            "latest_snapshot": availability.get("latest"),
            "total_snapshots": len(history),
            "snapshot_history": history[:10],
            "change_analysis": changes,
            "trajectory": self._assess_trajectory(history, changes),
        }

    def _check_availability(self) -> dict:
        try:
            r = requests.get(
                f"http://archive.org/wayback/available?url={self.domain}",
                timeout=10
            )
            data = r.json()
            snap = data.get("archived_snapshots", {}).get("closest", {})
            return {
                "available": snap.get("available", False),
                "latest": snap.get("timestamp"),
                "latest_url": snap.get("url"),
            }
        except Exception:
            return {"available": False}

    def _get_snapshot_history(self) -> list:
        try:
            r = requests.get(
                f"http://web.archive.org/cdx/search/cdx",
                params={
                    "url": self.domain,
                    "output": "json",
                    "limit": 50,
                    "fl": "timestamp,statuscode",
                    "filter": "statuscode:200",
                    "collapse": "timestamp:6",  # one per month
                },
                timeout=15
            )
            data = r.json()
            if not data or len(data) < 2:
                return []

            snapshots = []
            for row in data[1:]:  # skip header
                try:
                    ts = row[0]
                    year = int(ts[:4])
                    month = int(ts[4:6])
                    snapshots.append({
                        "timestamp": ts,
                        "year": year,
                        "month": month,
                        "date_str": f"{year}-{month:02d}",
                    })
                except Exception:
                    continue
            return snapshots
        except Exception:
            return []

    def _analyze_changes(self, history: list) -> dict:
        if not history:
            return {"data_available": False}

        years = [s["year"] for s in history]
        if not years:
            return {"data_available": False}

        earliest_year = min(years)
        latest_year = max(years)
        age_years = latest_year - earliest_year

        # Count snapshots per year to detect activity levels
        from collections import Counter
        year_counts = Counter(years)
        recent_years = sorted(year_counts.keys())[-3:]
        recent_activity = sum(year_counts[y] for y in recent_years)
        older_years = sorted(year_counts.keys())[:-3]
        older_activity = sum(year_counts[y] for y in older_years) if older_years else 0

        # Detect if they're updating more or less frequently
        if recent_activity > older_activity * 1.5:
            update_trend = "increasing"
        elif recent_activity < older_activity * 0.5:
            update_trend = "decreasing"
        else:
            update_trend = "stable"

        # Estimate last major redesign based on snapshot density gaps
        last_redesign_year = None
        if len(years) > 5:
            for i in range(len(years) - 1, 0, -1):
                if years[i] - years[i-1] >= 2:
                    last_redesign_year = years[i]
                    break

        return {
            "data_available": True,
            "site_age_years": age_years,
            "established_since": earliest_year,
            "total_archived_months": len(history),
            "update_frequency_trend": update_trend,
            "recent_activity_score": recent_activity,
            "estimated_last_redesign": last_redesign_year,
            "snapshots_by_year": dict(year_counts),
        }

    def _assess_trajectory(self, history: list, changes: dict) -> dict:
        if not changes.get("data_available"):
            return {"signal": "No archive data available"}

        signals = []
        age = changes.get("site_age_years", 0)
        trend = changes.get("update_frequency_trend", "stable")
        recent = changes.get("recent_activity_score", 0)

        if age >= 10:
            signals.append(f"Established business — online since ~{changes.get('established_since')}")
        elif age >= 5:
            signals.append(f"Mid-stage business — ~{age} years online")
        else:
            signals.append(f"Relatively new online presence — ~{age} years")

        if trend == "decreasing":
            signals.append("Site update frequency declining — possible neglect or stagnation")
        elif trend == "increasing":
            signals.append("Site update frequency increasing — active and growing online")

        if recent < 3:
            signals.append("Very few recent snapshots — site may not be updated regularly")

        redesign = changes.get("estimated_last_redesign")
        if redesign:
            years_since = datetime.now().year - redesign
            if years_since >= 4:
                signals.append(f"Possible last major redesign ~{redesign} — {years_since} years ago")

        return {
            "signals": signals,
            "site_age_years": age,
            "established_since": changes.get("established_since"),
            "update_trend": trend,
            "cold_email_angle": f"Site established since {changes.get('established_since')} but update frequency has been {trend}" if changes.get("established_since") else None,
        }
