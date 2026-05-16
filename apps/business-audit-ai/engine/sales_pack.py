"""
Sales pack generation for turning an audit into customer-acquisition assets.

This module deliberately avoids paid APIs. It uses the audit facts already
collected by the app and creates practical scripts, positioning, follow-up
tasks, and a simple rule-based fallback when the LLM key is unavailable.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlparse


def _domain(url: str) -> str:
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    return parsed.netloc.replace("www.", "") or parsed.path.replace("www.", "")


def _money(value) -> str:
    try:
        return f"${int(float(value)):,}"
    except (TypeError, ValueError):
        return "$1,500+"


def _first_truthy(*values, default=""):
    for value in values:
        if value:
            return value
    return default


def _industry(audit_data: dict, business_name: str) -> str:
    return _first_truthy(
        audit_data.get("competitors", {}).get("inferred_business_type"),
        audit_data.get("industry", {}).get("industry"),
        business_name,
        default="local business",
    )


def _location(audit_data: dict) -> str:
    return _first_truthy(
        audit_data.get("competitors", {}).get("inferred_location"),
        audit_data.get("gbp", {}).get("location"),
        default="their market",
    )


def _contact(audit_data: dict) -> dict:
    website = audit_data.get("website", {})
    trust = website.get("trust_signals", {})
    homepage = website.get("homepage", {})
    pages = website.get("internal_pages", {})
    emails = list(homepage.get("email_addresses") or [])
    phones = list(homepage.get("phone_numbers") or [])
    for page in pages.values():
        emails.extend(page.get("email_addresses") or [])
        phones.extend(page.get("phone_numbers") or [])
    return {
        "email": _first_truthy(trust.get("email"), homepage.get("email"), emails[0] if emails else ""),
        "phone": _first_truthy(trust.get("phone"), homepage.get("phone"), phones[0] if phones else ""),
        "address": _first_truthy(trust.get("address"), homepage.get("address")),
    }


def free_mode_quality(audit_data: dict) -> dict:
    website = audit_data.get("website", {})
    homepage = website.get("homepage", {})
    global_signals = website.get("global_signals", {})
    conversion = website.get("conversion_signals", {})
    trust = website.get("trust_signals", {})
    technical = website.get("technical_signals", {})
    forms = homepage.get("forms", {})

    checks = [
        ("CTA above fold", bool(conversion.get("above_fold_cta") or homepage.get("has_cta_buttons", {}).get("above_fold_cta")),
         "Add one direct booking/call CTA in the first screen."),
        ("Contact page", bool(conversion.get("contact_page_exists") or "contact" in global_signals.get("pages_found", [])),
         "Create or strengthen the contact page and link it in navigation."),
        ("Contact form", bool(conversion.get("contact_form_exists") or forms.get("count")),
         "Add a short form with name, phone/email, and service needed."),
        ("Phone visible", bool(trust.get("has_phone_number") or homepage.get("phone_numbers")),
         "Put the phone number in the header and mobile sticky area."),
        ("Live chat or instant response", bool(global_signals.get("has_live_chat") or conversion.get("has_chat_widget")),
         "Add AI chat or instant SMS/email follow-up for inquiries."),
        ("Booking system", bool(conversion.get("booking_system")),
         "Add a booking link or appointment request flow."),
        ("Social proof", bool(homepage.get("has_testimonials", {}).get("has_testimonials") or trust.get("has_google_reviews_widget")),
         "Show reviews/testimonials near CTAs."),
        ("Analytics installed", bool(technical.get("has_google_analytics") or technical.get("has_tag_manager")),
         "Install analytics before running growth experiments."),
        ("Mobile viewport", bool(technical.get("meta_viewport")),
         "Add responsive viewport metadata if missing."),
        ("HTTPS", bool(technical.get("has_ssl") or global_signals.get("has_ssl_indicators")),
         "Use HTTPS and avoid trust warnings."),
    ]

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = [{"name": name, "fix": fix} for name, ok, fix in checks if not ok]
    return {
        "score": round((passed / len(checks)) * 100),
        "passed": passed,
        "total": len(checks),
        "failed": failed,
        "highest_priority_fix": failed[0]["fix"] if failed else "Use the audit to improve the strongest existing offer.",
    }


def _top_findings(audit_data: dict) -> list[dict]:
    findings = []

    performance = audit_data.get("performance", {})
    load_time = performance.get("load_time_seconds") or performance.get("metrics", {}).get("load_time_seconds")
    mobile_score = performance.get("mobile_score") or performance.get("performance_score")
    if load_time and load_time > 3:
        findings.append({
            "category": "performance",
            "title": "Slow mobile experience",
            "finding": f"Homepage appears to load in about {load_time:.1f}s, which is likely costing mobile inquiries.",
            "impact": "Lower form fills, fewer calls, and weaker ad conversion.",
            "solution": "AI Lead Capture + speed cleanup",
            "urgency": "high",
        })
    elif mobile_score and mobile_score < 70:
        findings.append({
            "category": "performance",
            "title": "Weak page performance",
            "finding": f"Performance score is {mobile_score}/100, creating friction before prospects contact them.",
            "impact": "More visitors leave before becoming leads.",
            "solution": "AI landing page rewrite + technical cleanup",
            "urgency": "high",
        })

    website = audit_data.get("website", {})
    global_signals = website.get("global_signals", {})
    if not global_signals.get("has_live_chat"):
        findings.append({
            "category": "conversion",
            "title": "No instant lead response",
            "finding": "No live chat or instant response layer was detected on the site.",
            "impact": "Visitors with buying intent may leave instead of waiting for a callback.",
            "solution": "AI Receptionist",
            "urgency": "critical",
        })
    if "contact" in global_signals.get("missing_key_pages", []):
        findings.append({
            "category": "conversion",
            "title": "Contact path is weak",
            "finding": "The audit did not find a strong contact page in the key site navigation.",
            "impact": "Ready-to-buy visitors have a harder time taking the next step.",
            "solution": "AI Lead Capture funnel",
            "urgency": "high",
        })

    seo = audit_data.get("seo", {})
    seo_score = seo.get("overall_score") or seo.get("seo_score")
    missing_pages = seo.get("content_gaps", {}).get("missing_key_pages") or global_signals.get("missing_key_pages", [])
    if seo_score and seo_score < 70:
        findings.append({
            "category": "seo",
            "title": "Organic search gap",
            "finding": f"SEO score is {seo_score}/100, so buyers searching locally may not find them first.",
            "impact": "Competitors can capture high-intent searches.",
            "solution": "AI Local SEO Content System",
            "urgency": "high",
        })
    elif missing_pages:
        findings.append({
            "category": "seo",
            "title": "Missing buyer pages",
            "finding": f"Missing or weak key pages: {', '.join(missing_pages[:3])}.",
            "impact": "Less search visibility and fewer persuasive landing pages.",
            "solution": "AI Service Page Builder",
            "urgency": "medium",
        })

    reviews = audit_data.get("reviews", {}).get("assessment", {})
    review_count = reviews.get("google_review_count") or 0
    rating = reviews.get("google_rating")
    if review_count and review_count < 25:
        findings.append({
            "category": "reviews",
            "title": "Review volume is thin",
            "finding": f"Google profile shows about {review_count} reviews.",
            "impact": "Lower trust than competitors with stronger review volume.",
            "solution": "AI Review Request Engine",
            "urgency": "medium",
        })
    if rating and rating < 4.4:
        findings.append({
            "category": "reviews",
            "title": "Reputation risk",
            "finding": f"Google rating appears to be {rating} stars.",
            "impact": "Prospects may compare alternatives before calling.",
            "solution": "AI Reputation Monitor",
            "urgency": "high",
        })

    social = audit_data.get("social", {})
    missing_social = social.get("missing_platforms") or social.get("missing") or []
    if missing_social:
        findings.append({
            "category": "social",
            "title": "Social proof gap",
            "finding": f"Missing or weak social presence on: {', '.join(missing_social[:3])}.",
            "impact": "Less trust when prospects check them before calling.",
            "solution": "AI Social Proof Engine",
            "urgency": "medium",
        })

    return findings[:5]


def heuristic_insights(url: str, business_name: str, audit_data: dict) -> dict:
    """Create a useful audit summary without an LLM key."""
    findings = _top_findings(audit_data)
    industry = _industry(audit_data, business_name)
    traffic = audit_data.get("traffic", {})
    monthly_leak = (
        audit_data.get("funnel", {})
        .get("revenue_leak", {})
        .get("estimated_monthly_revenue_leak")
    )
    score = 72 - (len(findings) * 7)
    if monthly_leak:
        score -= 8
    score = max(25, min(88, score))

    if not findings:
        findings = [{
            "category": "conversion",
            "title": "Lead follow-up opportunity",
            "finding": "The site has enough public signals to justify a faster inquiry follow-up workflow.",
            "impact": "Speed-to-lead improvements can create more booked calls from existing traffic.",
            "solution": "AI Receptionist",
            "urgency": "medium",
        }]

    top_insights = []
    for index, item in enumerate(findings, 1):
        top_insights.append({
            "rank": index,
            "title": item["title"],
            "category": item["category"],
            "finding": item["finding"],
            "why_it_matters": item["impact"],
            "benchmark": "Fast follow-up and clearer conversion paths usually improve lead capture for local service businesses.",
            "citation": "Rule-based local audit heuristic",
            "data_sources": [item["category"]],
            "estimated_impact": _first_truthy(
                f"~{_money(monthly_leak)}/month possible leak" if monthly_leak else "",
                "Likely lost calls or form fills from existing traffic",
            ),
            "ai_solution": {
                "name": item["solution"],
                "what_it_does": f"Captures and qualifies {industry} inquiries immediately, then routes hot leads to the owner.",
                "how_it_works": "Add a lightweight chat/form/SMS workflow using free or low-cost tools first. Use the audit finding as the opening offer.",
                "timeline": "Live in 3-7 days",
                "specific_outcome": "More inquiries answered without hiring staff",
                "monthly_roi": _money(monthly_leak) if monthly_leak else "1-3 extra jobs can cover the build",
            },
            "urgency": item["urgency"],
        })

    visitors = traffic.get("estimated_monthly_visitors")
    business_label = business_name or _domain(url)
    return {
        "business_summary": (
            f"{business_label} looks like a {industry} with clear room to improve lead capture. "
            f"The highest-leverage issue is {top_insights[0]['title'].lower()}."
        ),
        "overall_health_score": score,
        "top_insights": top_insights,
        "ai_growth_plan": [
            {
                "phase": 1,
                "name": "Phase 1 - Capture Existing Demand",
                "solutions": ["AI Receptionist", "AI Lead Capture"],
                "combined_impact": "Make every website visitor and missed inquiry easier to convert.",
                "estimated_monthly_value": _money(monthly_leak) if monthly_leak else "$500-$2,500/month",
            },
            {
                "phase": 2,
                "name": "Phase 2 - Build Trust",
                "solutions": ["AI Review Engine", "AI Follow-up"],
                "combined_impact": "Increase review volume and speed up post-inquiry follow-up.",
                "estimated_monthly_value": "$1,000-$4,000/month",
            },
            {
                "phase": 3,
                "name": "Phase 3 - Compound Search",
                "solutions": ["AI Local SEO Content System"],
                "combined_impact": "Publish service and local pages that capture high-intent searches.",
                "estimated_monthly_value": "$2,000+/month",
            },
        ],
        "total_ai_opportunity": (
            f"{_money(monthly_leak)}/month in likely revenue leakage from the current funnel."
            if monthly_leak else
            "The clearest opportunity is converting more of the traffic they already have before spending on ads."
        ),
        "most_urgent_ai_solution": top_insights[0]["ai_solution"]["name"],
        "funnel_summary": "Focus first on speed-to-lead, contact friction, and proof.",
        "competitor_gap_summary": "Use the audit to show one specific gap competitors can exploit.",
        "quick_wins": [
            "Add a one-click call or booking CTA above the fold.",
            "Install a simple AI FAQ/intake assistant for common buyer questions.",
            "Create a 3-message follow-up sequence for new form submissions.",
            "Ask recent happy customers for reviews with an automated text/email flow.",
        ],
        "biggest_opportunity": f"Build a lightweight AI Receptionist for {business_label} that answers, qualifies, and routes leads within minutes.",
        "_mode": "free_rule_based",
    }


def heuristic_email(url: str, business_name: str, insights: dict) -> dict:
    business = business_name or _domain(url)
    top = (insights.get("top_insights") or [{}])[0]
    solution = top.get("ai_solution", {}).get("name", "AI Receptionist")
    subject = f"{business}: {top.get('title', 'lead follow-up gap')}"
    body = (
        f"{business} has a clear {top.get('title', 'lead follow-up')} issue: {top.get('finding', 'the site is leaving inquiries harder to convert')}.\n\n"
        f"That usually means potential customers leave before calling or booking. I can set up a small {solution} that answers common questions, qualifies leads, and pushes hot inquiries to you quickly.\n\n"
        "Worth a quick call this week?"
    )
    return {
        "subject_line": subject[:80],
        "email": body,
        "why_this_works": "It opens with a specific finding and sells one practical fix.",
        "alternative_subject": f"Quick idea for {business}",
        "_mode": "free_rule_based",
    }


def heuristic_email_sequence(url: str, business_name: str, insights: dict, audit_data: dict) -> dict:
    business = business_name or _domain(url)
    industry = _industry(audit_data, business_name)
    top = (insights.get("top_insights") or [{}])[0]
    second = (insights.get("top_insights") or [{}, {}])[1] if len(insights.get("top_insights", [])) > 1 else top
    solution = top.get("ai_solution", {}).get("name", "AI Receptionist")
    finding = top.get("finding", "your website could convert more of the traffic it already gets")
    return {
        "sequence": [
            {
                "email_number": 1,
                "send_day": 0,
                "subject": f"{business}: {top.get('title', 'lead capture gap')}",
                "body": f"{business} has a specific gap: {finding} I can set up a small {solution} so more visitors become booked calls. Worth a quick call this week?",
                "angle": "specific audit finding",
            },
            {
                "email_number": 2,
                "send_day": 3,
                "subject": f"{industry} leads are won fast",
                "body": f"Following up because this is usually a speed problem. When a {industry} prospect is ready, the business that responds first often gets the conversation. I can show you the exact workflow I would add for {business}.",
                "angle": "speed-to-lead",
            },
            {
                "email_number": 3,
                "send_day": 7,
                "subject": "7-day pilot idea",
                "body": f"Instead of a big project, I would start with a 7-day pilot: one AI intake flow, one follow-up sequence, and one clear metric. If it does not create better conversations for {business}, you stop there.",
                "angle": "low-risk pilot",
            },
            {
                "email_number": 4,
                "send_day": 14,
                "subject": f"Another gap: {second.get('title', 'follow-up')}",
                "body": f"Different angle: {second.get('finding', 'there is still conversion friction on the site')} This can be fixed without rebuilding the whole site. I can send over the simple version if useful.",
                "angle": "second pain point",
            },
            {
                "email_number": 5,
                "send_day": 21,
                "subject": "Should I close the loop?",
                "body": f"Haven't heard back, so I will close the loop. Leaving this here in case lead follow-up becomes a priority: {business} could start with a small AI receptionist instead of a full website rebuild.",
                "angle": "breakup",
            },
        ],
        "sequence_summary": "This sequence stays specific, offers a small pilot, and avoids sounding like generic AI consulting.",
        "_mode": "free_rule_based",
    }


def sales_pack(url: str, business_name: str, audit_data: dict, insights: dict, email: dict, email_sequence: dict) -> dict:
    business = business_name or _domain(url)
    industry = _industry(audit_data, business_name)
    location = _location(audit_data)
    contact = _contact(audit_data)
    top = (insights.get("top_insights") or [{}])[0]
    top_solution = top.get("ai_solution", {})
    offer_name = top_solution.get("name") or "AI Receptionist"
    today = datetime.utcnow().date()
    quality = free_mode_quality(audit_data)

    lead_score = 45
    if insights.get("overall_health_score", 100) < 60:
        lead_score += 18
    if quality.get("score", 100) < 60:
        lead_score += 12
    if contact.get("email") or contact.get("phone"):
        lead_score += 10
    if audit_data.get("funnel", {}).get("revenue_leak", {}).get("estimated_monthly_revenue_leak"):
        lead_score += 12
    if audit_data.get("website", {}).get("global_signals", {}).get("has_live_chat") is False:
        lead_score += 10
    lead_score = min(100, lead_score)

    cta = "Want me to send a 2-minute walkthrough?"
    audit_finding = top.get("finding", "their site is leaving leads harder to convert")
    one_liner = f"I help {industry} businesses in {location} turn more website visitors into booked calls with practical AI follow-up."
    pilot = (
        f"7-day {offer_name} pilot: build one intake/follow-up workflow, connect it to their current email or form, "
        "and measure replies, calls, or booked appointments."
    )
    demo_workflow = [
        "Visitor lands on website or submits form",
        "AI asks 2-4 qualifying questions",
        "Hot lead gets an instant reply with booking/call options",
        "Owner receives a summary with urgency, service need, and contact details",
        "Lead is added to a simple tracking sheet",
        "Follow-up messages go out until they book or decline",
    ]
    proposal = {
        "title": f"{offer_name} pilot for {business}",
        "problem": audit_finding,
        "scope": [
            "Audit-backed intake/follow-up workflow",
            "FAQ and qualification prompts",
            "Owner notification template",
            "Simple tracking sheet",
            "Three-message follow-up sequence",
        ],
        "timeline": "3-7 days",
        "success_metric": "More replies, booked calls, qualified leads, or saved admin time.",
        "price_options": [
            {"name": "Free walkthrough", "price": "$0", "includes": "Audit explanation and pilot plan"},
            {"name": "Starter pilot", "price": "$300-$750", "includes": "One working AI intake/follow-up workflow"},
            {"name": "Done-with-you pilot", "price": "$750-$1,500", "includes": "Workflow, tracking, scripts, and 14 days of iteration"},
        ],
    }
    outreach_score = score_outreach(email.get("email", ""), audit_finding)

    return {
        "lead_score": lead_score,
        "best_buyer": "Owner, office manager, marketing manager, or operator responsible for incoming leads.",
        "one_liner": one_liner,
        "audit_hook": audit_finding,
        "pilot_offer": pilot,
        "price_anchor": "Start free/cheap: offer a no-obligation audit walkthrough, then sell a small pilot. Do not mention expensive retainers first.",
        "free_stack": [
            "Google Sheets or the built-in SQLite lead table for CRM",
            "Gmail manual sending with copy/paste templates",
            "Google Calendar booking link",
            "Tally/Google Forms for intake",
            "Zapier free tier, Make free tier, or manual setup for the first pilot",
            "Groq free tier for AI copy and summaries",
            "Loom free tier or phone screen recording for custom walkthroughs",
        ],
        "quality_check": quality,
        "outreach_score": outreach_score,
        "demo_workflow": demo_workflow,
        "scripts": {
            "permission_email": (
                f"Subject: quick idea for {business}\n\n"
                f"Noticed one thing on {business}'s site: {audit_finding}\n\n"
                f"I build small AI systems for {industry} businesses that respond to inquiries faster and qualify leads automatically.\n\n"
                f"{cta}"
            ),
            "linkedin_dm": (
                f"Quick idea for {business}: {audit_finding} I help {industry} businesses add AI lead follow-up without changing their current tools. "
                "Open to me sending the idea?"
            ),
            "phone_opener": (
                f"Hi, I had a quick website idea for {business}. I noticed {audit_finding} "
                "and wanted to ask who handles new customer inquiries or website leads."
            ),
            "referral_ask": (
                f"I am looking for 3 {industry} businesses to test a small AI lead follow-up pilot. "
                "Do you know anyone who gets website inquiries and wants faster response without hiring?"
            ),
        },
        "walkthrough_outline": [
            "Show their website and the exact issue from the audit.",
            "Explain the lost lead scenario in plain language.",
            f"Show the proposed {offer_name} workflow in 3 steps.",
            "Offer the 7-day pilot and one metric you will track.",
        ],
        "follow_up_plan": [
            {"day": 0, "date": str(today), "task": "Send permission email or LinkedIn DM."},
            {"day": 1, "date": str(today + timedelta(days=1)), "task": "Send 2-minute walkthrough if they reply or open conversation."},
            {"day": 3, "date": str(today + timedelta(days=3)), "task": "Follow up with speed-to-lead angle."},
            {"day": 7, "date": str(today + timedelta(days=7)), "task": "Offer 7-day pilot with one measurable outcome."},
            {"day": 14, "date": str(today + timedelta(days=14)), "task": "Use the second finding as a fresh angle."},
            {"day": 21, "date": str(today + timedelta(days=21)), "task": "Breakup email and move to nurture."},
        ],
        "proposal_outline": [
            f"Problem: {audit_finding}",
            f"Pilot: {pilot}",
            "Deliverables: intake assistant, follow-up sequence, owner notification, simple tracking sheet.",
            "Timeline: 3-7 days for first working version.",
            "Success metric: replies, booked calls, qualified leads, or saved admin time.",
        ],
        "proposal": proposal,
        "mailto": {
            "subject": email.get("subject_line", f"Quick idea for {business}"),
            "body": email.get("email", ""),
            "to": contact.get("email", ""),
        },
        "crm_row": {
            "business_name": business,
            "url": url,
            "industry": industry,
            "location": location,
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "lead_score": lead_score,
            "status": "new",
            "hook": audit_finding,
            "offer": offer_name,
            "next_step": "Send permission email",
        },
    }


def score_outreach(email_body: str, audit_finding: str) -> dict:
    body = email_body or ""
    words = body.split()
    checks = {
        "uses_audit_fact": bool(audit_finding and audit_finding[:28].lower() in body.lower()),
        "under_140_words": len(words) <= 140,
        "clear_cta": any(phrase in body.lower() for phrase in ["quick call", "send", "worth", "open to", "useful"]),
        "one_problem": body.lower().count(" and ") < 5,
        "not_generic": not any(phrase in body.lower() for phrase in ["hope this finds you well", "synergy", "cutting-edge", "revolutionize"]),
    }
    score = sum(20 for passed in checks.values() if passed)
    suggestions = []
    if not checks["uses_audit_fact"]:
        suggestions.append("Lead with one exact audit finding.")
    if not checks["under_140_words"]:
        suggestions.append("Cut the email under 140 words.")
    if not checks["clear_cta"]:
        suggestions.append("End with one low-friction question.")
    if not checks["one_problem"]:
        suggestions.append("Focus on one problem, not every audit issue.")
    if not checks["not_generic"]:
        suggestions.append("Remove generic AI consulting language.")
    return {"score": score, "checks": checks, "suggestions": suggestions}
