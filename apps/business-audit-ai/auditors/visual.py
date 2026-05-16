"""
Visual Analysis Auditor — screenshots the homepage via ScreenshotOne API
and sends it to an AI vision model to catch what no HTML scraper can:
  - Is the design outdated?
  - Is the CTA visible above the fold?
  - Is there a clear value proposition in the first 3 seconds?
  - Is it cluttered / wall of text?
  - Are trust signals visible?

Uses ScreenshotOne API (free tier: 100 screenshots/month).
Get a free key at: https://screenshotone.com
Add to .env: SCREENSHOTONE_API_KEY=your_key

Falls back gracefully if key is not set.
"""
import base64
import json
import os
import requests
from typing import Optional


VISION_PROMPT = """You are a conversion rate optimization expert analyzing a screenshot of a business website homepage.

Your job is to identify SPECIFIC, ACTIONABLE problems visible in the screenshot that are costing this business customers RIGHT NOW.

Analyze these dimensions:
1. FIRST IMPRESSION (0-3 second test): Is there a clear, compelling headline immediately visible? Can you tell what they do in 3 seconds?
2. CTA VISIBILITY: Is there a clear call-to-action button above the fold? What color/text? Is it prominent or buried?
3. DESIGN ERA: Does this look modern (2022+), dated (2015-2021), or very outdated (pre-2015)?
4. TRUST SIGNALS: Are testimonials, star ratings, client logos, certifications, or social proof visible without scrolling?
5. VISUAL CLUTTER: Is the layout clean and scannable, or is it overwhelming with too much information?
6. VALUE PROPOSITION: Is it immediately clear WHY someone should choose this business over competitors?
7. MOBILE READINESS: Does the layout look responsive and clean (even if viewed on desktop)?
8. HERO SECTION QUALITY: Is the hero image/video professional and relevant, or generic/stock?

Return ONLY a JSON object (no other text):
{
  "first_impression_score": <0-100>,
  "headline_visible": <true/false>,
  "headline_text": "<exact headline text you can see, or null>",
  "cta_above_fold": <true/false>,
  "cta_text": "<exact CTA button text you can see, or null>",
  "cta_prominence": "dominant|visible|buried|missing",
  "design_era": "modern|dated|very_dated",
  "design_score": <0-100>,
  "trust_signals_visible": <true/false>,
  "trust_signal_types": ["<list of trust signals you can actually see>"],
  "visual_clutter": "clean|moderate|cluttered|overwhelming",
  "value_prop_clarity": "crystal_clear|moderate|vague|missing",
  "hero_quality": "professional|adequate|poor|stock_photo",
  "overall_grade": "A|B|C|D|F",
  "overall_score": <0-100>,
  "top_issues": [
    "<specific issue 1 — be exact, e.g. 'The main CTA button is gray on white, nearly invisible'>",
    "<specific issue 2>",
    "<specific issue 3>"
  ],
  "whats_working": "<one specific thing done well, or null>",
  "most_urgent_fix": "<the single most impactful visual change they could make today>",
  "cold_email_angle": "<one punchy sentence about the most obvious visual problem, suitable for a cold email opening>"
}"""


class VisualAuditor:
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
        self.screenshot_api_key = os.getenv("SCREENSHOTONE_API_KEY")

    def audit(self) -> dict:
        if not self.screenshot_api_key:
            return {"skipped": True, "reason": "SCREENSHOTONE_API_KEY not set"}

        screenshot_b64 = self._take_screenshot()
        if not screenshot_b64:
            return {"skipped": True, "reason": "Screenshot failed"}

        analysis = self._analyze_with_vision(screenshot_b64)
        return {
            "screenshot_taken": True,
            "analysis": analysis,
            "overall_score": analysis.get("overall_score"),
            "overall_grade": analysis.get("overall_grade"),
            "top_issues": analysis.get("top_issues", []),
            "cold_email_angle": analysis.get("cold_email_angle"),
            "design_era": analysis.get("design_era"),
            "cta_above_fold": analysis.get("cta_above_fold"),
            "value_prop_clarity": analysis.get("value_prop_clarity"),
        }

    def _take_screenshot(self) -> Optional[str]:
        """Fetch screenshot via ScreenshotOne API, return as base64 string."""
        try:
            params = {
                "access_key": self.screenshot_api_key,
                "url": self.url,
                "viewport_width": 1280,
                "viewport_height": 900,
                "full_page": "false",
                "format": "png",
                "block_cookie_banners": "true",
                "block_ads": "true",
                "delay": 2,
                "timeout": 20,
            }
            response = requests.get(
                "https://api.screenshotone.com/take",
                params=params,
                timeout=30,
            )
            if response.status_code == 200 and response.content:
                return base64.b64encode(response.content).decode("utf-8")
            return None
        except Exception:
            return None

    def _analyze_with_vision(self, image_b64: str) -> dict:
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            vision_models = [
                "meta-llama/llama-4-maverick-17b-128e-instruct",
                "meta-llama/llama-4-scout-17b-16e-instruct",
                "llama-3.2-90b-vision-preview",
                "llama-3.2-11b-vision-preview",
            ]

            last_error = None
            for model in vision_models:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        max_tokens=1200,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                                {"type": "text", "text": VISION_PROMPT},
                            ],
                        }],
                    )
                    raw = response.choices[0].message.content
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(raw[start:end])
                    return {"raw": raw, "parse_error": True}
                except Exception as e:
                    last_error = str(e)
                    if "model" in str(e).lower() or "not found" in str(e).lower():
                        continue
                    break

            return {"error": last_error or "Vision analysis failed"}

        except Exception as e:
            return {"error": str(e)}
