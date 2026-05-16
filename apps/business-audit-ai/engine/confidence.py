"""
Confidence Scoring Engine
Evaluates each finding's credibility based on how many independent data sources
corroborate it and whether the values are directly measured vs. estimated.

Levels:
  HIGH      — 3+ corroborating sources OR direct measurement + 1 benchmark
  MEDIUM    — 2 sources, or 1 direct measurement
  LOW       — 1 indirect source, or aggregated proxy
  ESTIMATED — No direct measurement; industry average only
"""

from typing import Optional


# Maps audit module → measurement type
# "direct"    = actually fetched from the site / API
# "inferred"  = calculated from signals
# "estimated" = educated guess from public data
MODULE_QUALITY = {
    "website":          "direct",
    "performance":      "direct",
    "seo":              "direct",
    "dns_intel":        "direct",
    "tech_stack":       "direct",
    "visual":           "direct",
    "reviews":          "direct",
    "social":           "direct",
    "ads":              "inferred",
    "competitors":      "inferred",
    "content_deep":     "direct",
    "funnel":           "inferred",
    "review_sentiment": "inferred",
    "wayback":          "direct",
    "traffic":          "estimated",
    "trends":           "direct",
    "jobs":             "direct",
    "industry":         "inferred",
}

# Category → which modules are relevant evidence
CATEGORY_SOURCES = {
    "performance": ["performance", "website", "funnel", "traffic"],
    "seo":         ["seo", "website", "competitors", "trends", "traffic"],
    "reviews":     ["reviews", "review_sentiment", "competitors", "website"],
    "conversion":  ["website", "content_deep", "funnel", "visual", "tech_stack"],
    "social":      ["social", "website", "competitors"],
    "content":     ["content_deep", "website", "seo", "competitors"],
    "competitors": ["competitors", "seo", "traffic", "trends"],
    "ads":         ["ads", "website", "tech_stack"],
    "funnel":      ["funnel", "website", "performance", "content_deep", "visual"],
    "trends":      ["trends", "industry"],
    "tech":        ["tech_stack", "dns_intel", "website"],
    "visual":      ["visual", "content_deep", "funnel"],
}


def score_finding(
    category: str,
    audit_data: dict,
    required_modules: Optional[list] = None,
) -> dict:
    """
    Returns a confidence dict for a single finding.

    Args:
        category: finding category (e.g. "performance", "seo")
        audit_data: the full audit_data dict
        required_modules: optional list of specific modules that must have data

    Returns:
        {
          "level": "HIGH" | "MEDIUM" | "LOW" | "ESTIMATED",
          "score": 0-100,
          "sources_present": [...],
          "sources_missing": [...],
          "measurement_quality": "direct" | "inferred" | "estimated",
          "confidence_note": "Human-readable explanation"
        }
    """
    relevant = CATEGORY_SOURCES.get(category, list(audit_data.keys()))
    if required_modules:
        relevant = list(set(relevant + required_modules))

    sources_present = []
    sources_missing = []
    quality_levels = []

    for mod in relevant:
        data = audit_data.get(mod)
        if data and not _is_error_only(data):
            sources_present.append(mod)
            quality_levels.append(MODULE_QUALITY.get(mod, "estimated"))
        else:
            sources_missing.append(mod)

    n_present = len(sources_present)
    n_direct = quality_levels.count("direct")
    n_inferred = quality_levels.count("inferred")

    # Score calculation
    if n_present == 0:
        level = "ESTIMATED"
        score = 15
    elif n_present == 1 and n_direct == 0:
        level = "LOW"
        score = 30
    elif n_present == 1 and n_direct == 1:
        level = "MEDIUM"
        score = 55
    elif n_present == 2 and n_direct >= 1:
        level = "MEDIUM"
        score = 65
    elif n_present >= 3 and n_direct >= 2:
        level = "HIGH"
        score = 85
    elif n_present >= 2:
        level = "MEDIUM"
        score = 60
    else:
        level = "LOW"
        score = 35

    # Bonus for direct measurements
    score = min(score + n_direct * 3, 95)

    # Best quality of present sources
    if n_direct > 0:
        measurement_quality = "direct"
    elif n_inferred > 0:
        measurement_quality = "inferred"
    else:
        measurement_quality = "estimated"

    # Human note
    if level == "HIGH":
        note = f"Backed by {n_present} data sources ({n_direct} direct measurements)"
    elif level == "MEDIUM":
        note = f"Based on {n_present} sources; {n_direct} direct + {n_inferred} inferred"
    elif level == "LOW":
        note = f"Limited data ({n_present} source). Treat as directional signal."
    else:
        note = "No direct data — industry average estimate only"

    return {
        "level": level,
        "score": score,
        "sources_present": sources_present,
        "sources_missing": sources_missing,
        "measurement_quality": measurement_quality,
        "confidence_note": note,
    }


def score_all_findings(insights: dict, audit_data: dict) -> dict:
    """
    Attaches confidence scores to every finding in the insights dict.
    Mutates insights in-place and returns it.
    """
    for finding in insights.get("top_insights", []):
        category = finding.get("category", "")
        finding["confidence"] = score_finding(category, audit_data)

    # Score the growth plan phases (aggregate)
    overall_present = [
        m for m in audit_data
        if audit_data[m] and not _is_error_only(audit_data[m])
    ]
    insights["data_coverage"] = {
        "modules_with_data": overall_present,
        "modules_total": len(audit_data),
        "coverage_percent": round(len(overall_present) / max(len(audit_data), 1) * 100),
    }

    return insights


def _is_error_only(data) -> bool:
    """Returns True if the data dict is just {"error": "..."}."""
    if not isinstance(data, dict):
        return False
    return list(data.keys()) == ["error"]
