"""
Email Sequence Generator — produces a full 5-email cold outreach sequence.
Each email hits a different angle so even non-responders eventually convert.
Email 1: Surprising specific finding
Email 2 (Day 3): Competitor angle
Email 3 (Day 7): Case study / social proof
Email 4 (Day 14): Different pain point
Email 5 (Day 21): Breakup email
"""
import json
import os
from groq import Groq



SYSTEM_PROMPT = """You are a cold email sequence specialist for an AI services company.
You write 5-email outreach sequences that get responses through persistence and relevance.

Each email is SHORT (under 100 words), hits a DIFFERENT angle, and references SPECIFIC data about the prospect.

EMAIL SEQUENCE STRUCTURE:
Email 1 — The Surprising Finding: Open with their most surprising specific weakness + exact number. Name the AI solution. CTA: "Worth a quick call?"
Email 2 — The Competitor Angle (Day 3): "While you were [problem], your competitor [specific competitor name if available] [is doing X]." Create urgency through competition.
Email 3 — The Case Study (Day 7): "We helped a [same business type] in [similar location] go from [before] to [after] in [timeframe]." Make it feel achievable and real.
Email 4 — The Different Pain Point (Day 14): Pick their 2nd or 3rd biggest finding. Fresh angle, don't repeat Email 1.
Email 5 — The Breakup (Day 21): Short, direct. "Haven't heard back — maybe [problem] isn't a priority right now. Leaving this here in case it is: [one line value prop]. No hard feelings either way."

RULES:
- Every email references their business name
- Every email has a specific number from the audit
- Subject lines always reference a number or specific situation
- No "I hope this finds you well" ever
- Sound like a human who did real research, not a template
- Each email is under 100 words

OUTPUT FORMAT — return JSON:
{
  "sequence": [
    {
      "email_number": 1,
      "send_day": 0,
      "subject": "subject line with specific number",
      "body": "email body under 100 words",
      "angle": "what this email's hook is"
    },
    ... (5 total)
  ],
  "sequence_summary": "1 sentence on why this sequence will work for this specific business"
}"""


class EmailSequenceWriter:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", api_key))

    def write(self, url: str, business_name: str, insights: dict, audit_data: dict) -> dict:
        top_insights = insights.get("top_insights", [])
        biz_summary = insights.get("business_summary", "")
        competitors = audit_data.get("competitors", {}).get("competitors_found", [])
        competitor_name = competitors[0].get("name", "a competitor") if competitors else "a competitor"
        industry = audit_data.get("competitors", {}).get("inferred_business_type", "business")
        location = audit_data.get("competitors", {}).get("inferred_location", "your area")
        reviews = audit_data.get("reviews", {}).get("assessment", {})
        jobs = audit_data.get("jobs", {}).get("analysis", {})
        traffic = audit_data.get("traffic", {})

        context = f"""
BUSINESS: {business_name or url}
WHAT THEY DO: {biz_summary}
INDUSTRY: {industry}
LOCATION: {location}
COMPETITOR NAME: {competitor_name}

KEY DATA POINTS:
- Google rating: {reviews.get('google_rating', 'unknown')} ({reviews.get('google_review_count', '?')} reviews)
- Estimated monthly visitors: {traffic.get('estimated_monthly_visitors', '~500')}
- Estimated monthly leads: {traffic.get('revenue_context', {}).get('estimated_monthly_leads', '?')}

TOP 3 FINDINGS:
{json.dumps(top_insights[:3], indent=2)}

JOBS SIGNAL:
{json.dumps(jobs.get('primary_insight', {}), indent=2) if jobs.get('primary_insight') else 'No hiring data found'}

AI GROWTH PLAN:
{json.dumps(insights.get('ai_growth_plan', [])[:2], indent=2)}

Write a 5-email sequence. Use the competitor name in Email 2. Use the industry type for the Email 3 case study. Make each email feel like it was written specifically for this business.
"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=3000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
        )

        raw = response.choices[0].message.content

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {"raw": raw, "parse_error": True}
