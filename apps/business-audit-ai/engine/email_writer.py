"""
Email Writer — generates personalized, insight-driven cold emails.
Uses the top 2-3 insights to write an email that feels like it was researched specifically for the prospect.
"""
import json
import os
from groq import Groq



SYSTEM_PROMPT = """You are a cold email specialist for an AI services company. You write short, devastating cold emails that make business owners feel like you've been watching their business — and that you have the exact AI solution for their exact problem.

STRUCTURE — follow this exactly, 4 sentences max:
1. One specific, surprising finding about THEIR business with an exact number (not generic)
2. What that's costing them in customers or revenue (make it feel real and urgent)
3. Name the exact AI solution that fixes it — sound like a product, not a service ("our AI Review Engine" / "AI chatbot trained on your catalog" / "AI content system targeting [their keyword gap]")
4. "Worth a quick call this week?"

RULES:
- Open with the finding, NOT with who you are or "I noticed..."
- Use their business name at least once
- Every number must come from the actual audit data — no made-up stats
- The AI solution mentioned should be SPECIFIC to their business type and situation
- Subject line must contain a specific number or dollar figure
- Under 120 words total
- Sound human, not robotic

OUTPUT FORMAT — return JSON:
{
  "subject_line": "subject with a specific number",
  "email": "the 4-sentence email",
  "why_this_works": "1 sentence on why this specific angle will get a response",
  "alternative_subject": "second subject option"
}"""


class EmailWriter:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", api_key))

    def write(self, url: str, business_name: str, insights: dict) -> dict:
        top_insights = insights.get("top_insights", [])[:3]
        biggest_opp = insights.get("biggest_opportunity", "")
        biz_summary = insights.get("business_summary", "")
        most_urgent = insights.get("most_urgent_ai_solution", "")
        total_opportunity = insights.get("total_ai_opportunity", "")

        # Pull the top AI solution detail for specificity
        top_ai_solution = None
        if top_insights and top_insights[0].get("ai_solution"):
            top_ai_solution = top_insights[0]["ai_solution"]

        user_message = f"""
Write a cold email for this business prospect. You are selling AI services.

BUSINESS: {business_name or url}
WHAT THEY DO: {biz_summary}

MOST URGENT AI OPPORTUNITY:
{most_urgent}

TOTAL AI OPPORTUNITY:
{total_opportunity}

TOP FINDING + AI SOLUTION (this is your email angle):
{json.dumps(top_insights[0], indent=2) if top_insights else 'None'}

ADDITIONAL FINDINGS FOR CONTEXT:
{json.dumps(top_insights[1:], indent=2)}

Write the 4-sentence cold email. Reference the specific AI solution by name. Make the business owner feel like you've done your homework on their specific situation.
"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )

        raw = response.choices[0].message.content

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {"email": raw, "parse_error": True}
