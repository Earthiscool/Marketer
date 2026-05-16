"""
Customer Journey & Funnel Auditor — maps the complete experience
a potential customer has from finding the business to contacting them.
Identifies every friction point and quantifies the drop-off at each stage.
"""
import re
from typing import Optional


class FunnelAuditor:
    def __init__(
        self,
        url: str,
        website_data: dict,
        performance_data: dict,
        seo_data: dict,
        monthly_visitors: int = 500,
        avg_customer_value: int = 500,
    ):
        self.url = url
        self.website_data = website_data
        self.performance_data = performance_data
        self.seo_data = seo_data
        self.monthly_visitors = monthly_visitors
        self.avg_customer_value = avg_customer_value

    def audit(self) -> dict:
        stages = self._map_funnel_stages()
        friction_points = self._identify_friction_points(stages)
        revenue_leak = self._calculate_revenue_leak(stages, friction_points)

        return {
            "funnel_stages": stages,
            "friction_points": friction_points,
            "revenue_leak": revenue_leak,
            "customer_experience_score": self._score_experience(stages),
            "journey_map": self._generate_journey_map(stages, friction_points),
        }

    def _map_funnel_stages(self) -> dict:
        perf = self.performance_data.get("summary", {})
        seo = self.seo_data
        site = self.website_data
        conv = site.get("conversion_signals", {})
        trust = site.get("trust_signals", {})
        homepage = site.get("homepage", {})
        global_sig = site.get("global_signals", {})

        mobile_score = perf.get("mobile_performance_score") or 0
        lcp = perf.get("estimated_lcp_seconds") or 3.0
        seo_score = seo.get("seo_score", {}).get("score") or 50

        discovery_score = min(100, seo_score)
        discovery_loss = 100 - discovery_score

        load_abandonment = 0
        if lcp > 5:
            load_abandonment = 60
        elif lcp > 3:
            load_abandonment = 40
        elif lcp > 2:
            load_abandonment = 15
        else:
            load_abandonment = 5

        has_clear_vp = bool(homepage.get("h1_tags"))
        has_above_fold_cta = conv.get("above_fold_cta", False)
        has_trust = trust.get("has_phone_number") or trust.get("has_physical_address")
        engagement_score = sum([has_clear_vp, has_above_fold_cta, has_trust, global_sig.get("has_video_content", False)]) * 25

        forms = homepage.get("forms", {})
        form_list = forms.get("forms", [])
        avg_fields = sum(f.get("field_count", 0) for f in form_list) / max(len(form_list), 1)
        has_booking = conv.get("booking_system", False)
        has_chat = conv.get("has_chat_widget", False)
        has_free_offer = conv.get("has_free_offer", False)

        friction_penalty = 0
        if avg_fields > 5:
            friction_penalty += 20
        if not has_booking and not has_chat:
            friction_penalty += 15
        if not has_free_offer:
            friction_penalty += 10
        if not conv.get("has_money_back_guarantee"):
            friction_penalty += 10

        action_score = max(0, 100 - friction_penalty)

        return {
            "stage_1_discovery": {
                "name": "Discovery (Can they find you?)",
                "score": discovery_score,
                "estimated_visitors_reaching": 100,
                "signals": {
                    "seo_score": seo_score,
                    "has_blog": seo.get("page_coverage", {}).get("has_blog_for_seo", False),
                    "local_seo_setup": not seo.get("local_seo", {}).get("missing_local_schema", True),
                    "ranking_keywords": seo.get("keyword_signals", {}).get("heading_keyword_count", 0),
                },
                "issue": f"Weak SEO ({seo_score}/100) — most potential customers can't find you in search",
            },
            "stage_2_first_impression": {
                "name": "First Impression (Do they stay?)",
                "score": max(0, 100 - load_abandonment),
                "estimated_visitors_reaching": round(100 * (1 - load_abandonment / 100)),
                "load_time_seconds": lcp,
                "mobile_score": mobile_score,
                "abandonment_rate": load_abandonment,
                "signals": {
                    "page_speed": perf.get("mobile_grade", "unknown"),
                    "mobile_optimized": mobile_score >= 50,
                },
                "issue": f"Page loads in {lcp}s — ~{load_abandonment}% of visitors leave before the page finishes loading",
            },
            "stage_3_engagement": {
                "name": "Engagement (Do they want to learn more?)",
                "score": engagement_score,
                "estimated_visitors_reaching": round(100 * (1 - load_abandonment / 100) * (engagement_score / 100)),
                "signals": {
                    "clear_value_proposition": has_clear_vp,
                    "above_fold_cta": has_above_fold_cta,
                    "trust_signals_visible": has_trust,
                    "video_content": global_sig.get("has_video_content", False),
                    "has_social_proof": conv.get("has_social_proof_numbers", False),
                },
                "issue": "Unclear value proposition and missing trust signals cause visitors to bounce without engaging" if engagement_score < 50 else None,
            },
            "stage_4_consideration": {
                "name": "Consideration (Do they trust you enough to act?)",
                "score": min(100, round((trust.get("social_link_count", 0) * 5 +
                               (20 if trust.get("has_certifications") else 0) +
                               (20 if global_sig.get("has_guarantee") else 0) +
                               (20 if trust.get("has_case_studies") else 0) +
                               (20 if trust.get("has_client_logos") else 0)), 0)),
                "signals": {
                    "has_testimonials": site.get("homepage", {}).get("has_testimonials", {}).get("has_testimonials", False),
                    "has_guarantee": global_sig.get("has_guarantee", False),
                    "has_certifications": trust.get("has_certifications", False),
                    "has_case_studies": trust.get("has_case_studies", False),
                    "has_press": global_sig.get("has_press_mentions", False),
                },
                "issue": "Insufficient trust signals — visitors can't verify you're credible before contacting" if not trust.get("has_certifications") and not global_sig.get("has_guarantee") else None,
            },
            "stage_5_conversion": {
                "name": "Conversion (Do they actually contact you?)",
                "score": action_score,
                "signals": {
                    "contact_form": bool(forms.get("count", 0)),
                    "avg_form_fields": round(avg_fields, 1),
                    "has_booking": has_booking,
                    "has_live_chat": has_chat,
                    "has_free_offer": has_free_offer,
                    "has_phone_visible": trust.get("has_phone_number", False),
                    "multiple_contact_options": sum([bool(forms.get("count")), has_booking, has_chat, trust.get("has_phone_number", False)]) >= 2,
                },
                "issue": f"High-friction conversion — {round(avg_fields, 0)}-field forms, no booking system, no free offer" if friction_penalty > 30 else None,
            },
        }

    def _identify_friction_points(self, stages: dict) -> list:
        friction = []

        for stage_key, stage in stages.items():
            score = stage.get("score", 100)
            issue = stage.get("issue")
            if score < 60 and issue:
                severity = "critical" if score < 30 else "high" if score < 50 else "medium"
                friction.append({
                    "stage": stage["name"],
                    "score": score,
                    "severity": severity,
                    "issue": issue,
                    "visitors_lost_here": 100 - stage.get("estimated_visitors_reaching", score),
                })

        friction.sort(key=lambda x: x["score"])
        return friction

    def _calculate_revenue_leak(self, stages: dict, friction_points: list) -> dict:
        final_stage = stages.get("stage_5_conversion", {})
        final_visitors = final_stage.get("estimated_visitors_reaching", 10)

        actual_converting = self.monthly_visitors * (final_visitors / 100)
        potential_with_fixes = self.monthly_visitors * 0.15
        monthly_gap = max(0, potential_with_fixes - actual_converting)

        monthly_revenue_leak = round(monthly_gap * self.avg_customer_value)

        return {
            "estimated_monthly_visitors": self.monthly_visitors,
            "estimated_converting_now": round(actual_converting),
            "potential_with_optimizations": round(potential_with_fixes),
            "monthly_leads_being_lost": round(monthly_gap),
            "estimated_monthly_revenue_leak": monthly_revenue_leak,
            "estimated_annual_revenue_leak": monthly_revenue_leak * 12,
            "note": f"Based on {self.monthly_visitors} monthly visitors and ${self.avg_customer_value} avg customer value. Pass real numbers via monthly_visitors and avg_customer_value for accurate projections.",
            "biggest_leak": friction_points[0]["stage"] if friction_points else "Unknown",
            "summary": f"Funnel analysis suggests ~{round(monthly_gap)} leads/month are leaking through fixable gaps, representing ~${monthly_revenue_leak:,}/month in potential revenue.",
        }

    def _score_experience(self, stages: dict) -> dict:
        scores = [s.get("score", 0) for s in stages.values()]
        avg = sum(scores) / len(scores) if scores else 0
        weakest = min(stages.items(), key=lambda x: x[1].get("score", 100))

        return {
            "overall_score": round(avg),
            "grade": "Excellent" if avg >= 80 else "Good" if avg >= 65 else "Needs Work" if avg >= 45 else "Poor",
            "weakest_stage": weakest[1]["name"] if weakest else "Unknown",
            "weakest_score": weakest[1].get("score", 0) if weakest else 0,
            "stage_scores": {k: v.get("score", 0) for k, v in stages.items()},
        }

    def _generate_journey_map(self, stages: dict, friction: list) -> list:
        journey = []
        for stage_key, stage in stages.items():
            visitors = stage.get("estimated_visitors_reaching", 100)
            score = stage.get("score", 100)
            status = "good" if score >= 70 else "warning" if score >= 50 else "critical"

            journey.append({
                "step": stage["name"],
                "visitors_remaining": visitors,
                "score": score,
                "status": status,
                "bottleneck": score < 50,
            })

        return journey
