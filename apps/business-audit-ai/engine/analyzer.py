"""
Insight Analyzer — the brain of the system.
Uses Claude to deeply analyze all audit data and generate specific, quantified business insights.
This is what turns raw data into "because your site loads in 5.8s you're losing 43% of customers."

Two-pass analysis:
  Pass 1 — Extract raw measurements (no recommendations, no benchmarks, just facts from data)
  Pass 2 — Write findings WITH citations, using Pass 1 facts as grounding
"""
import json
import os
from groq import Groq
from data.benchmarks import get_benchmark_context


PASS1_SYSTEM = """You are a data extraction agent. Your ONLY job is to pull raw measurements out of the audit JSON.
DO NOT give recommendations. DO NOT mention benchmarks. DO NOT suggest solutions.
Just extract FACTS: exact numbers, exact scores, what's present/absent, what competitors have.

Return a JSON object with keys:
{
  "performance_facts": ["Page load time: Xs", "Mobile score: N/100", ...],
  "seo_facts": ["SEO score: N/100", "Missing H1: yes/no", ...],
  "review_facts": ["Google rating: N stars", "Review count: N", ...],
  "conversion_facts": ["Live chat: yes/no", "Above-fold CTA: yes/no", ...],
  "social_facts": ["Platforms active: [...]", "Missing: [...]", ...],
  "content_facts": ["Word count: N", "Blog: yes/no", ...],
  "competitor_facts": ["Competitor X has live chat, you don't", ...],
  "tech_stack_facts": ["Uses: [...]", "Missing: [...]", ...],
  "visual_facts": ["Visual score: N/100", "Design era: ...", ...],
  "traffic_facts": ["Est. monthly visitors: N", ...],
  "funnel_facts": ["Weakest stage: ...", "Monthly revenue leak: $...", ...],
  "top_5_weakest_areas": ["area1", "area2", "area3", "area4", "area5"]
}
Only include facts that are actually present in the data. Never invent."""

PASS2_SYSTEM = """You are the AI strategy lead at an AI services company. You have raw audit measurements AND verified facts extracted from the data.

Your job:
1. Identify the TOP 5 most damaging weaknesses using ONLY facts from the extracted data
2. For each weakness, prescribe the EXACT AI solution with specific ROI
3. EVERY statistic you cite MUST include its source in parentheses — no bare numbers

RULES FOR FINDINGS:
- Quote EXACT numbers from the extracted facts (e.g. "your site loaded in 5.8s")
- Every benchmark citation MUST be in format: "stat (Source, Year)"
- Compound weak signals when multiple data points support a single problem
- Use competitor data when present: "Competitor X has live chat, you don't"
- Connect every finding to lost revenue or lost customers

CITATION RULE — MANDATORY:
Every benchmark number in your response MUST have its source cited. Example:
  WRONG: "53% of mobile users abandon slow sites"
  RIGHT: "53% of mobile users abandon slow sites (Google/SOASTA Research, 2017)"

AI SOLUTIONS MENU:
- AI Chatbot: handles FAQs, qualifies leads, books appointments 24/7
- AI Review Engine: automated post-purchase review requests + AI replies
- AI Content System: SEO blog posts weekly targeting competitor keyword gaps
- AI Local SEO System: optimizes GMB profile, builds local landing pages
- AI Lead Capture: exit-intent popups, smart forms, automated follow-up sequences
- AI Ad Manager: A/B tests ad copy, manages retargeting, builds lookalike audiences
- AI Social Media Engine: generates and schedules platform-specific content daily
- AI Reputation Monitor: monitors all review platforms 24/7, generates response drafts
- AI Sales Funnel: rewrites landing page copy, implements dynamic CTAs, A/B tests
- AI Competitor Tracker: monitors competitor pricing, content, and ads weekly

OUTPUT FORMAT — return a JSON object with this EXACT structure:
{
  "business_summary": "2-3 sentences: what they do, market position, single biggest thing holding them back",
  "overall_health_score": 0-100,
  "top_insights": [
    {
      "rank": 1,
      "title": "Short punchy title (max 8 words)",
      "category": "performance|seo|reviews|conversion|social|content|competitors|ads|funnel|trends",
      "finding": "SPECIFIC thing found — exact numbers from extracted facts",
      "why_it_matters": "What this costs them RIGHT NOW — customers or revenue",
      "benchmark": "The industry stat WITH citation in parentheses: 'X% do Y (Source, Year)'",
      "citation": "Full citation: Author/Organization, Study Title, Year",
      "data_sources": ["list", "of", "audit", "modules", "that", "support", "this"],
      "estimated_impact": "Specific: '~43% of mobile visitors leave' or '~$3,200/month in lost leads'",
      "ai_solution": {
        "name": "AI [Product Name]",
        "what_it_does": "Exactly what the AI does for THIS business — mention their specific context",
        "how_it_works": "2-3 sentences on mechanics — what gets built, how it runs",
        "timeline": "Live in X weeks",
        "specific_outcome": "Quantified result: '+340 organic visitors/month within 90 days'",
        "monthly_roi": "Estimated $ value or leads recovered per month"
      },
      "urgency": "critical|high|medium"
    }
  ],
  "ai_growth_plan": [
    {
      "phase": 1,
      "name": "Phase 1 — Quick Wins (Week 1-2)",
      "solutions": ["AI solution names"],
      "combined_impact": "What this phase accomplishes",
      "estimated_monthly_value": "$X,XXX/month"
    },
    {
      "phase": 2,
      "name": "Phase 2 — Growth Engine (Month 1-2)",
      "solutions": ["AI solution names"],
      "combined_impact": "What this adds",
      "estimated_monthly_value": "$X,XXX/month"
    },
    {
      "phase": 3,
      "name": "Phase 3 — Market Dominance (Month 2-4)",
      "solutions": ["AI solution names"],
      "combined_impact": "Long-term compounding effects",
      "estimated_monthly_value": "$X,XXX/month"
    }
  ],
  "total_ai_opportunity": "Total estimated monthly value with brief cited reasoning",
  "most_urgent_ai_solution": "Single highest-ROI AI solution and why",
  "funnel_summary": "Where in the customer journey they lose the most people",
  "competitor_gap_summary": "How competitors are beating them and how AI closes gaps",
  "quick_wins": ["3-5 things doable in days"],
  "biggest_opportunity": "The one AI deployment that transforms this business — specific, quantified"
}"""


class InsightAnalyzer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", api_key))
        self.model = "llama-3.3-70b-versatile"

    def analyze(self, url: str, business_name: str, audit_data: dict) -> dict:
        audit_summary = self._prepare_audit_summary(audit_data)
        benchmarks = get_benchmark_context()

        # ── PASS 1: Extract key facts (lightweight — avoids token overload) ──
        pass1_message = f"""Extract the most important measurable facts from this audit data.
Be brief. Just list key numbers and yes/no signals.

URL: {url} | Business: {business_name or 'Unknown'}

AUDIT DATA:
{json.dumps(audit_summary, indent=2)}

Return JSON with keys: performance_facts, seo_facts, review_facts, conversion_facts,
social_facts, competitor_facts, top_5_weakest_areas"""

        raw_facts = self._call_groq(
            system=PASS1_SYSTEM,
            user=pass1_message,
            max_tokens=800,
            label="Pass 1",
        )

        # ── PASS 2: Full analysis using extracted facts + benchmarks ──────────
        # Do NOT resend full audit_summary — use extracted facts only
        facts_str = json.dumps(raw_facts, indent=2) if isinstance(raw_facts, dict) and "parse_error" not in raw_facts else "Facts extraction failed — use audit data above"

        pass2_message = f"""Write a full business audit analysis for this business.

URL: {url} | Business: {business_name or 'Unknown'}

KEY FACTS EXTRACTED FROM AUDIT:
{facts_str}

CITED BENCHMARKS (cite sources in parentheses for every stat):
{benchmarks}

Return the complete JSON analysis. Every benchmark stat MUST have its source cited in parentheses."""

        insights = self._call_groq(
            system=PASS2_SYSTEM,
            user=pass2_message,
            max_tokens=4000,
            label="Pass 2",
        )

        # ── Fallback: single-pass if 2-pass failed ────────────────────────────
        if not isinstance(insights, dict) or "parse_error" in insights:
            insights = self._single_pass_fallback(url, business_name, audit_summary, benchmarks)

        if not isinstance(insights, dict) or "parse_error" in insights:
            return insights

        insights["_extracted_facts"] = raw_facts

        # ── Confidence scores + fix simulations ───────────────────────────────
        try:
            from engine.confidence import score_all_findings
            from engine.fix_simulator import simulate_all_findings
            insights = score_all_findings(insights, audit_data)
            insights = simulate_all_findings(insights, audit_data)
        except Exception as e:
            insights["_tier3_error"] = str(e)

        return insights

    def _single_pass_fallback(self, url, business_name, audit_summary, benchmarks) -> dict:
        """Simpler single-pass prompt — used when 2-pass fails."""
        message = f"""Analyze this business audit and identify the top 5 weaknesses.

URL: {url} | Business: {business_name or 'Unknown'}

AUDIT DATA:
{json.dumps(audit_summary, indent=2)}

BENCHMARKS:
{benchmarks}

Return JSON matching the exact format specified. Cite all benchmark sources in parentheses."""

        return self._call_groq(
            system=PASS2_SYSTEM,
            user=message,
            max_tokens=4000,
            label="Fallback",
        )

    def _call_groq(self, system: str, user: str, max_tokens: int, label: str) -> dict:
        """Call Groq and parse JSON. Returns dict (possibly with parse_error)."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            raw = response.choices[0].message.content
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                return {"raw": raw, "parse_error": f"{label}: no JSON found"}
            return json.loads(raw[start:end])
        except json.JSONDecodeError as e:
            return {"parse_error": f"{label}: JSON parse error — {e}"}
        except Exception as e:
            return {"parse_error": f"{label}: {e}"}

    def _prepare_audit_summary(self, audit_data: dict) -> dict:
        summary = {}

        if "website" in audit_data:
            w = audit_data["website"]
            summary["website"] = {
                "homepage_word_count": w.get("homepage", {}).get("word_count"),
                "title": w.get("homepage", {}).get("title"),
                "h1_tags": w.get("homepage", {}).get("h1_tags"),
                "has_ctas": w.get("homepage", {}).get("has_cta_buttons"),
                "forms": w.get("homepage", {}).get("forms"),
                "missing_pages": w.get("global_signals", {}).get("missing_key_pages"),
                "has_live_chat": w.get("global_signals", {}).get("has_live_chat"),
                "has_guarantee": w.get("global_signals", {}).get("has_guarantee"),
                "has_video": w.get("global_signals", {}).get("has_video_content"),
                "trust_signals": {
                    "social_links_count": w.get("trust_signals", {}).get("social_link_count"),
                    "platforms": w.get("trust_signals", {}).get("social_links_found"),
                    "has_address": w.get("trust_signals", {}).get("has_physical_address"),
                    "has_phone": w.get("trust_signals", {}).get("has_phone_number"),
                    "has_certifications": w.get("trust_signals", {}).get("has_certifications"),
                    "years_in_business": w.get("trust_signals", {}).get("has_years_in_business"),
                },
                "conversion": {
                    "above_fold_cta": w.get("conversion_signals", {}).get("above_fold_cta"),
                    "has_free_offer": w.get("conversion_signals", {}).get("has_free_offer"),
                    "has_booking_system": w.get("conversion_signals", {}).get("booking_system"),
                    "has_chat_widget": w.get("conversion_signals", {}).get("has_chat_widget"),
                    "has_money_back": w.get("conversion_signals", {}).get("has_money_back_guarantee"),
                    "social_proof_numbers": w.get("conversion_signals", {}).get("has_social_proof_numbers"),
                },
                "content": {
                    "has_blog": w.get("content_signals", {}).get("has_blog"),
                    "has_how_it_works": w.get("content_signals", {}).get("has_how_it_works"),
                    "value_prop": w.get("content_signals", {}).get("value_proposition_clarity"),
                    "readability": w.get("content_signals", {}).get("readability_estimate"),
                },
                "analytics": {
                    "has_google_analytics": w.get("technical_signals", {}).get("has_google_analytics"),
                    "has_facebook_pixel": w.get("technical_signals", {}).get("has_facebook_pixel"),
                    "cms": w.get("technical_signals", {}).get("cms_detected"),
                },
            }

        if "performance" in audit_data:
            p = audit_data["performance"]
            summary["performance"] = {
                "mobile_score": p.get("summary", {}).get("mobile_performance_score"),
                "desktop_score": p.get("summary", {}).get("desktop_performance_score"),
                "lcp_seconds": p.get("summary", {}).get("estimated_lcp_seconds"),
                "mobile_grade": p.get("summary", {}).get("mobile_grade"),
                "visitor_loss_estimate": p.get("summary", {}).get("visitor_loss_estimate"),
                "mobile_core_vitals": p.get("mobile", {}).get("core_web_vitals") if isinstance(p.get("mobile"), dict) else None,
                "mobile_top_issues": p.get("mobile", {}).get("top_opportunities") if isinstance(p.get("mobile"), dict) else None,
            }

        if "seo" in audit_data:
            s = audit_data["seo"]
            summary["seo"] = {
                "score": s.get("seo_score", {}).get("score"),
                "grade": s.get("seo_score", {}).get("grade"),
                "title_issue": s.get("title_analysis", {}).get("issue"),
                "heading_issue": s.get("heading_structure", {}).get("issue"),
                "missing_h1": s.get("heading_structure", {}).get("missing_h1"),
                "local_seo_issue": s.get("local_seo", {}).get("issue"),
                "missing_local_schema": s.get("local_seo", {}).get("missing_local_schema"),
                "content_grade": s.get("content_depth", {}).get("homepage_content_grade"),
                "content_issue": s.get("content_depth", {}).get("issue"),
                "no_blog": s.get("page_coverage", {}).get("no_blog"),
                "missing_pages": s.get("page_coverage", {}).get("seo_important_pages_missing"),
                "image_seo_issue": s.get("image_seo", {}).get("issue"),
                "alt_tags_missing": s.get("image_seo", {}).get("total_images_missing_alt"),
            }

        if "social" in audit_data:
            s = audit_data["social"]
            summary["social"] = {
                "platforms": s.get("platforms_linked"),
                "platform_count": s.get("platform_count"),
                "missing_platforms": s.get("missing_major_platforms"),
                "grade": s.get("overall_assessment", {}).get("grade"),
                "issues": s.get("overall_assessment", {}).get("issues"),
                "platform_details": s.get("platform_details"),
            }

        if "reviews" in audit_data:
            r = audit_data["reviews"]
            summary["reviews"] = {
                "google_rating": r.get("assessment", {}).get("google_rating"),
                "google_review_count": r.get("assessment", {}).get("google_review_count"),
                "grade": r.get("assessment", {}).get("grade"),
                "has_on_site_testimonials": r.get("on_site_reviews", {}).get("has_testimonials_section"),
                "has_case_studies": r.get("on_site_reviews", {}).get("has_case_studies"),
                "critical_issues": r.get("reputation_signals", {}).get("issues_found"),
            }

        if "competitors" in audit_data:
            c = audit_data["competitors"]
            summary["competitors"] = {
                "business_type": c.get("inferred_business_type"),
                "location": c.get("inferred_location"),
                "competitors_found": [
                    {
                        "name": comp.get("name"),
                        "url": comp.get("url"),
                        "has_blog": comp.get("has_blog"),
                        "has_live_chat": comp.get("has_live_chat"),
                        "has_free_offer": comp.get("has_free_offer"),
                        "has_booking": comp.get("has_booking"),
                        "social_platforms": comp.get("social_platforms"),
                        "has_video": comp.get("has_video"),
                    }
                    for comp in c.get("competitors_found", [])[:4]
                ],
                "gaps_vs_competitors": c.get("gaps", {}).get("gaps_vs_competitors", []),
                "competitor_features": c.get("gaps", {}).get("competitor_feature_adoption", {}),
            }

        if "ads" in audit_data:
            a = audit_data["ads"]
            summary["ads"] = {
                "running_facebook_ads": a.get("facebook_ads", {}).get("appears_to_run_ads"),
                "competitors_bidding_on_brand": a.get("google_ads", {}).get("competitors_running_ads_on_name"),
                "has_facebook_pixel": a.get("tracking_pixels", {}).get("has_facebook_pixel"),
                "has_google_analytics": a.get("tracking_pixels", {}).get("has_google_analytics"),
                "missing_tracking": a.get("tracking_pixels", {}).get("missing_tracking", []),
                "ad_maturity": a.get("ad_strategy_assessment", {}).get("ad_maturity"),
                "ad_issues": a.get("ad_strategy_assessment", {}).get("issues", []),
            }

        if "trends" in audit_data:
            t = audit_data["trends"]
            summary["trends"] = {
                "keyword": t.get("keyword_analyzed"),
                "direction": t.get("trend_direction", {}).get("direction"),
                "change_percent": t.get("trend_direction", {}).get("change_percent"),
                "seasonal_peaks": t.get("seasonal_peaks", {}).get("peak_months", []),
                "rising_keywords": [r.get("query") for r in t.get("rising_related_keywords", [])[:5]],
                "opportunity": t.get("opportunity_summary"),
                "error": t.get("error"),
            }

        if "content_deep" in audit_data:
            cd = audit_data["content_deep"]
            summary["content_deep"] = {
                "content_score": cd.get("content_score", {}).get("score"),
                "content_grade": cd.get("content_score", {}).get("grade"),
                "copy_is_self_focused": cd.get("copy_quality", {}).get("copy_is_self_focused"),
                "you_vs_we_ratio": cd.get("copy_quality", {}).get("you_vs_we_ratio"),
                "weak_phrases_found": cd.get("weak_phrases", {}).get("weak_phrases_found", [])[:5],
                "conversion_elements_missing": cd.get("conversion_elements", {}).get("elements_missing", []),
                "conversion_readiness_score": cd.get("conversion_elements", {}).get("conversion_readiness_score"),
                "value_prop_clarity": cd.get("value_proposition", {}).get("clarity"),
                "headline": cd.get("value_proposition", {}).get("headline"),
                "cta_quality_issue": cd.get("cta_quality", {}).get("issue"),
                "missing_elements": cd.get("missing_elements", []),
                "power_word_density": cd.get("power_words", {}).get("power_word_density"),
            }

        if "funnel" in audit_data:
            f = audit_data["funnel"]
            leak = f.get("revenue_leak", {})
            exp = f.get("customer_experience_score", {})
            summary["funnel"] = {
                "overall_experience_score": exp.get("overall_score"),
                "weakest_stage": exp.get("weakest_stage"),
                "weakest_score": exp.get("weakest_score"),
                "stage_scores": exp.get("stage_scores", {}),
                "friction_points": f.get("friction_points", []),
                "monthly_leads_lost": leak.get("monthly_leads_being_lost"),
                "monthly_revenue_leak": leak.get("estimated_monthly_revenue_leak"),
                "annual_revenue_leak": leak.get("estimated_annual_revenue_leak"),
                "journey_map": f.get("journey_map", []),
            }

        if "traffic" in audit_data:
            t = audit_data["traffic"]
            bench = t.get("benchmark_comparison", {})
            rev = t.get("revenue_context", {})
            summary["traffic"] = {
                "estimated_monthly_visitors": t.get("estimated_monthly_visitors"),
                "confidence": t.get("confidence"),
                "vs_industry_baseline_pct": bench.get("vs_baseline_pct"),
                "assessment": bench.get("assessment"),
                "industry_baseline": bench.get("industry_baseline"),
                "estimated_monthly_leads": rev.get("estimated_monthly_leads"),
                "optimized_leads_potential": rev.get("with_optimized_funnel"),
                "traffic_is_bottleneck": rev.get("traffic_is_the_bottleneck"),
                "conversion_is_bottleneck": rev.get("conversion_is_the_bottleneck"),
                "signals_used": t.get("signals_used", []),
            }

        if "industry" in audit_data:
            ind = audit_data["industry"]
            rev_model = ind.get("revenue_model", {})
            summary["industry"] = {
                "industry_type": ind.get("industry"),
                "profile_matched": ind.get("profile_matched"),
                "industry_score": ind.get("industry_score", {}).get("score"),
                "industry_grade": ind.get("industry_score", {}).get("grade"),
                "must_have_missing": ind.get("must_have_missing", []),
                "biggest_killers": ind.get("biggest_killers", []),
                "top_ai_opportunities": ind.get("top_ai_opportunities", []),
                "avg_customer_value": ind.get("avg_customer_value"),
                "key_benchmarks": ind.get("key_benchmarks", {}),
                "annual_revenue_opportunity": rev_model.get("annual_revenue_opportunity"),
                "monthly_revenue_opportunity": rev_model.get("monthly_revenue_opportunity"),
                "monthly_leads_gap": rev_model.get("monthly_leads_gap"),
            }

        if "wayback" in audit_data:
            wb = audit_data["wayback"]
            traj = wb.get("trajectory", {})
            changes = wb.get("change_analysis", {})
            summary["site_history"] = {
                "has_archive": wb.get("has_archive"),
                "site_age_years": changes.get("site_age_years"),
                "established_since": changes.get("established_since"),
                "update_trend": changes.get("update_frequency_trend"),
                "estimated_last_redesign": changes.get("estimated_last_redesign"),
                "trajectory_signals": traj.get("signals", []),
                "cold_email_angle": traj.get("cold_email_angle"),
            }

        if "review_sentiment" in audit_data:
            rs = audit_data["review_sentiment"]
            sentiment = rs.get("sentiment_breakdown", {})
            themes = rs.get("top_themes", {})
            summary["review_sentiment"] = {
                "reviews_analyzed": rs.get("reviews_analyzed"),
                "overall_sentiment": sentiment.get("overall"),
                "sentiment_score": sentiment.get("sentiment_score"),
                "positive_mentions": sentiment.get("positive_mentions"),
                "negative_mentions": sentiment.get("negative_mentions"),
                "top_negative_phrases": sentiment.get("top_negative_phrases", [])[:3],
                "top_positive_phrases": sentiment.get("top_positive_phrases", [])[:3],
                "top_themes": themes.get("top_themes", [])[:4],
                "insights": rs.get("insights", []),
            }

        if "jobs" in audit_data:
            j = audit_data["jobs"]
            summary["jobs"] = {
                "open_positions": j.get("open_positions_count"),
                "hiring_categories": j.get("hiring_categories", []),
                "primary_insight": j.get("analysis", {}).get("primary_insight"),
                "cold_email_angle": j.get("analysis", {}).get("cold_email_angle"),
            }

        if "tech_stack" in audit_data:
            ts = audit_data["tech_stack"]
            soph = ts.get("sophistication_score", {})
            summary["tech_stack"] = {
                "tools_detected": [t["name"] for t in ts.get("tools_detected", [])],
                "tool_count": ts.get("tool_count", 0),
                "grade": soph.get("grade"),
                "categories_present": list(ts.get("categories", {}).keys()),
                "missing_categories": [g["missing_category"] for g in ts.get("gaps", [])],
                "top_gaps": ts.get("gaps", [])[:4],
                "insights": ts.get("insights", [])[:3],
            }

        if "visual" in audit_data:
            v = audit_data["visual"]
            a = v.get("analysis", {})
            if not v.get("skipped") and not a.get("error"):
                summary["visual_analysis"] = {
                    "overall_score": v.get("overall_score"),
                    "overall_grade": v.get("overall_grade"),
                    "design_era": v.get("design_era"),
                    "cta_above_fold": v.get("cta_above_fold"),
                    "value_prop_clarity": v.get("value_prop_clarity"),
                    "top_issues": v.get("top_issues", []),
                    "most_urgent_fix": a.get("most_urgent_fix"),
                    "cold_email_angle": v.get("cold_email_angle"),
                    "trust_signals_visible": a.get("trust_signals_visible"),
                    "visual_clutter": a.get("visual_clutter"),
                    "hero_quality": a.get("hero_quality"),
                    "headline_text": a.get("headline_text"),
                }

        if "dns_intel" in audit_data:
            di = audit_data["dns_intel"]
            email_infra = di.get("email_infrastructure", {})
            ssl = di.get("ssl_intel", {})
            summary["dns_intel"] = {
                "email_provider": di.get("email_provider"),
                "email_infra_score": email_infra.get("score"),
                "email_infra_grade": email_infra.get("grade"),
                "has_spf": di.get("txt_records_summary", {}).get("has_spf"),
                "has_dmarc": di.get("txt_records_summary", {}).get("has_dmarc"),
                "domain_age_years": ssl.get("domain_age_from_ssl_years"),
                "subdomains": [s["prefix"] for s in di.get("subdomains_found", [])[:6]],
                "hosting_provider": di.get("hosting", {}).get("provider"),
                "email_infra_issues": email_infra.get("issues", [])[:3],
                "cold_email_angle": email_infra.get("cold_email_angle"),
            }

        return summary
