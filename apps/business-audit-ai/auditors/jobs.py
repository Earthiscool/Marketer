"""
Job Posting Intelligence — scrapes Indeed for the business's open roles.
Job postings reveal internal pain points: hiring 3 customer service reps = churn problem,
no open roles = stagnant or fully staffed, hiring sales = growth mode.
"""
import requests
import re
import random
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Optional


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


class JobsAuditor:
    def __init__(self, business_name: Optional[str], location: Optional[str] = None):
        self.business_name = business_name
        self.location = location

    def audit(self) -> dict:
        if not self.business_name:
            return {"skipped": True, "reason": "No business name provided"}

        jobs = self._scrape_indeed()
        analysis = self._analyze_jobs(jobs)

        return {
            "jobs_found": jobs,
            "total_open_roles": len(jobs),
            "analysis": analysis,
        }

    def _scrape_indeed(self) -> list:
        try:
            query = f"{self.business_name}"
            if self.location:
                url = f"https://www.indeed.com/jobs?q={quote_plus(query)}&l={quote_plus(self.location)}"
            else:
                url = f"https://www.indeed.com/jobs?q={quote_plus(query)}"

            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "lxml")
            jobs = []

            # Indeed job cards
            cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|cardOutline|tapItem"))
            if not cards:
                cards = soup.find_all("a", class_=re.compile(r"jobtitle|job-title"))

            for card in cards[:10]:
                title_el = card.find(["h2", "a"], class_=re.compile(r"jobtitle|title|jobTitle"))
                if not title_el:
                    title_el = card.find("h2")
                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                # Check if it's actually from this company
                company_el = card.find(class_=re.compile(r"company|companyName"))
                company = company_el.get_text(strip=True) if company_el else ""

                date_el = card.find(class_=re.compile(r"date|posted"))
                date = date_el.get_text(strip=True) if date_el else "Unknown"

                if self.business_name.lower()[:5] in company.lower() or not company:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "date_posted": date,
                    })

            return jobs
        except Exception as e:
            return []

    def _analyze_jobs(self, jobs: list) -> dict:
        if not jobs:
            return {
                "hiring_status": "No open roles found",
                "signal": "Either fully staffed, not using Indeed, or business is stagnant",
                "insights": [],
            }

        titles = [j["title"].lower() for j in jobs]
        all_titles = " ".join(titles)

        signals = []
        hiring_categories = {
            "customer_service": ["customer service", "support", "service rep", "client success"],
            "sales": ["sales", "account exec", "business development", "bdm", "bdr"],
            "marketing": ["marketing", "seo", "content", "social media", "growth"],
            "technical": ["developer", "engineer", "it ", "tech", "software"],
            "operations": ["operations", "manager", "coordinator", "admin"],
            "delivery_fulfillment": ["driver", "delivery", "fulfillment", "warehouse", "picker"],
        }

        found_categories = {}
        for category, keywords in hiring_categories.items():
            matching = [t for t in titles if any(kw in t for kw in keywords)]
            if matching:
                found_categories[category] = len(matching)

        # Generate insights from hiring patterns
        if found_categories.get("customer_service", 0) >= 2:
            signals.append({
                "finding": f"Hiring {found_categories['customer_service']} customer service roles simultaneously",
                "interpretation": "High volume of customer issues, churn, or rapid growth overwhelming support",
                "cold_email_angle": "AI chatbot could handle 40-60% of support volume, reducing hiring need",
            })

        if found_categories.get("sales", 0) >= 1:
            signals.append({
                "finding": f"Actively hiring {found_categories['sales']} sales role(s)",
                "interpretation": "In growth mode — prioritizing revenue generation",
                "cold_email_angle": "AI lead qualification could 3x the productivity of each new sales hire",
            })

        if found_categories.get("marketing", 0) >= 1:
            signals.append({
                "finding": f"Hiring {found_categories['marketing']} marketing role(s)",
                "interpretation": "Recognizes need for more marketing but paying full-time salary",
                "cold_email_angle": "AI content + SEO automation delivers same output at fraction of hiring cost",
            })

        if len(jobs) >= 5:
            signals.append({
                "finding": f"{len(jobs)} open roles at once",
                "interpretation": "Rapid scaling or high turnover — both are pain points",
                "cold_email_angle": "High growth or high churn = perfect candidate for AI automation",
            })

        return {
            "hiring_status": f"Actively hiring — {len(jobs)} open roles",
            "categories": found_categories,
            "signals": signals,
            "primary_insight": signals[0] if signals else None,
            "growth_mode": bool(found_categories.get("sales") or len(jobs) >= 3),
            "churn_signal": found_categories.get("customer_service", 0) >= 2,
        }
