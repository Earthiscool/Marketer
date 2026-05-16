"""
Industry-Specific Analyzer — applies different scoring weights and benchmarks
based on what type of business it is. A restaurant has completely different
critical success factors than a law firm or a SaaS company.
"""
from typing import Optional


INDUSTRY_PROFILES = {
    "restaurant": {
        "critical_signals": ["google_reviews", "google_maps_photos", "menu_online", "online_ordering", "reservation_system"],
        "must_have": ["GMB profile optimized", "50+ reviews", "online menu", "hours clearly listed", "photos"],
        "nice_to_have": ["online ordering", "reservation widget", "Instagram presence", "respond to all reviews"],
        "biggest_killers": ["bad reviews", "no photos on GMB", "menu not online", "not showing in maps"],
        "avg_customer_value": 45,
        "avg_visits_per_customer_year": 8,
        "key_benchmarks": {
            "avg_google_reviews": 87,
            "optimal_rating": 4.4,
            "yelp_importance": "critical",
            "mobile_traffic_share": 75,
        },
        "ai_opportunities": [
            "AI Review Response System — automatically responds to every review within minutes",
            "AI Menu Optimizer — analyzes which menu items drive highest margins and repeat visits",
            "AI Reservation Bot — handles bookings, waitlist, and reminders automatically",
            "AI Social Content Engine — generates daily food photos and stories with captions",
        ],
    },
    "pet store": {
        "critical_signals": ["product_catalog_online", "local_seo", "reviews", "social_proof", "email_capture"],
        "must_have": ["product catalog", "online ordering or store pickup", "loyalty program", "GMB profile"],
        "nice_to_have": ["blog content", "care guides", "vet referral network", "subscription service"],
        "biggest_killers": ["no online shopping", "no email list", "generic product pages", "no loyalty program"],
        "avg_customer_value": 800,
        "avg_visits_per_customer_year": 12,
        "key_benchmarks": {
            "avg_google_reviews": 45,
            "repeat_purchase_rate": 68,
            "email_marketing_roi": 4200,
        },
        "ai_opportunities": [
            "AI Product Recommendation Engine — shows personalized products based on pet type and purchase history",
            "AI Reorder Reminder — predicts when food/supplies run out and sends automated reminders",
            "AI Care Content System — generates weekly pet care tips that drive traffic and trust",
            "AI Loyalty Program Manager — personalizes rewards and re-engagement for lapsed customers",
        ],
    },
    "law firm": {
        "critical_signals": ["trust_signals", "case_results", "attorney_bios", "practice_areas", "lead_capture"],
        "must_have": ["attorney bios with photos", "practice areas clearly listed", "free consultation offer", "case results/wins"],
        "nice_to_have": ["blog with legal insights", "FAQ section", "live chat", "client testimonials"],
        "biggest_killers": ["no free consultation", "no trust signals", "weak attorney profiles", "no case results"],
        "avg_customer_value": 3500,
        "avg_visits_per_customer_year": 1.2,
        "key_benchmarks": {
            "avg_google_reviews": 28,
            "avg_conversion_rate": 3.2,
            "response_time_importance": "critical",
        },
        "ai_opportunities": [
            "AI Intake Bot — qualifies leads 24/7, collects case details, books consultations automatically",
            "AI Content Authority System — publishes legal guides targeting local search terms monthly",
            "AI Lead Nurture Sequences — automated follow-up for prospects who didn't book immediately",
            "AI Review Generation — automated post-case review requests with personalized messages",
        ],
    },
    "dental": {
        "critical_signals": ["online_booking", "insurance_info", "reviews", "before_after_photos", "new_patient_offer"],
        "must_have": ["online booking", "insurance accepted list", "new patient special", "reviews"],
        "nice_to_have": ["before/after gallery", "virtual consultation", "patient portal", "email reminders"],
        "biggest_killers": ["no online booking", "not accepting new patients clearly stated", "no new patient offer"],
        "avg_customer_value": 1800,
        "avg_visits_per_customer_year": 2,
        "key_benchmarks": {
            "avg_google_reviews": 52,
            "no_show_rate_avg": 18,
            "online_booking_preference": 68,
        },
        "ai_opportunities": [
            "AI Appointment Manager — handles booking, reminders, and reduces no-shows by 40%",
            "AI New Patient Acquisition — targets local searchers with personalized first-visit offers",
            "AI Review Engine — automated post-appointment review requests via SMS",
            "AI Treatment Plan Follow-up — nurtures patients who didn't schedule recommended treatments",
        ],
    },
    "plumbing": {
        "critical_signals": ["emergency_service", "local_seo", "reviews", "response_time", "trust_badges"],
        "must_have": ["24/7 emergency line", "service area clearly listed", "reviews", "licensing info"],
        "nice_to_have": ["online booking", "upfront pricing", "before/after photos", "guarantee"],
        "biggest_killers": ["no 24/7 contact", "not showing in local pack", "no reviews", "no trust badges"],
        "avg_customer_value": 450,
        "avg_visits_per_customer_year": 1.8,
        "key_benchmarks": {
            "avg_google_reviews": 34,
            "emergency_call_share": 45,
            "mobile_search_share": 72,
        },
        "ai_opportunities": [
            "AI Emergency Response Bot — captures leads 24/7 when they can't answer the phone",
            "AI Local SEO System — dominates local searches for every service + neighborhood combination",
            "AI Follow-up Sequences — converts one-time emergency customers into annual maintenance clients",
            "AI Review Request System — automated SMS review requests after job completion",
        ],
    },
    "real estate": {
        "critical_signals": ["listing_quality", "agent_profiles", "lead_capture", "neighborhood_content", "reviews"],
        "must_have": ["IDX/MLS integration", "agent bios", "neighborhood guides", "instant valuation tool"],
        "nice_to_have": ["virtual tours", "market reports", "buyer/seller guides", "live chat"],
        "biggest_killers": ["no lead capture", "no neighborhood content", "slow listing updates"],
        "avg_customer_value": 8500,
        "avg_visits_per_customer_year": 1,
        "key_benchmarks": {
            "avg_google_reviews": 22,
            "avg_conversion_rate": 0.8,
            "response_time_critical_hours": 5,
        },
        "ai_opportunities": [
            "AI Lead Qualification Bot — captures and scores buyer/seller leads 24/7",
            "AI Market Report Generator — personalized monthly reports for past clients and prospects",
            "AI Listing Description Writer — generates compelling MLS descriptions instantly",
            "AI Drip Campaign System — long-term nurture sequences for buyers not ready yet",
        ],
    },
    "marketing agency": {
        "critical_signals": ["case_studies", "portfolio", "pricing_transparency", "thought_leadership", "lead_magnet"],
        "must_have": ["case studies with results", "clear service descriptions", "free audit/assessment offer"],
        "nice_to_have": ["pricing guide", "blog with insights", "podcast/YouTube", "client logos"],
        "biggest_killers": ["no case study results", "vague service descriptions", "no free offer"],
        "avg_customer_value": 2500,
        "avg_visits_per_customer_year": 1.5,
        "key_benchmarks": {
            "avg_google_reviews": 15,
            "avg_conversion_rate": 2.1,
            "content_marketing_importance": "critical",
        },
        "ai_opportunities": [
            "AI Proposal Generator — creates customized proposals in minutes based on prospect research",
            "AI Content Engine — produces thought leadership content that demonstrates expertise",
            "AI Lead Scoring System — identifies which prospects are most likely to close",
            "AI Client Reporting System — automated monthly performance reports for all clients",
        ],
    },
    "HVAC": {
        "critical_signals": ["emergency_service", "local_seo", "seasonal_targeting", "maintenance_program", "reviews"],
        "must_have": ["24/7 emergency contact", "service areas", "maintenance plan info", "reviews"],
        "nice_to_have": ["online booking", "energy savings calculator", "seasonal promotions", "financing info"],
        "biggest_killers": ["not in local pack", "no maintenance program promotion", "no seasonal content"],
        "avg_customer_value": 850,
        "avg_visits_per_customer_year": 1.5,
        "key_benchmarks": {
            "avg_google_reviews": 41,
            "seasonal_demand_swings": "extreme",
            "maintenance_plan_upsell_value": 380,
        },
        "ai_opportunities": [
            "AI Seasonal Campaign Manager — automatically launches heating/cooling campaigns at peak demand",
            "AI Maintenance Reminder System — re-engages past customers before seasonal changeovers",
            "AI Emergency Lead Capture — captures after-hours emergency calls as leads automatically",
            "AI Local SEO Dominator — builds location + service pages for every neighborhood served",
        ],
    },
    "e-commerce": {
        "critical_signals": ["product_pages", "cart_abandonment", "email_capture", "reviews_on_products", "site_speed"],
        "must_have": ["fast site", "product reviews", "email capture", "abandoned cart recovery", "clear returns policy"],
        "nice_to_have": ["loyalty program", "subscription option", "product recommendations", "live chat"],
        "biggest_killers": ["slow site", "no cart recovery", "no product reviews", "complicated checkout"],
        "avg_customer_value": 120,
        "avg_visits_per_customer_year": 4,
        "key_benchmarks": {
            "avg_cart_abandonment": 70,
            "email_recovery_rate": 5,
            "avg_conversion_rate": 2.5,
            "repeat_purchase_rate": 35,
        },
        "ai_opportunities": [
            "AI Cart Recovery System — personalized abandoned cart emails/SMS that recover 8-15% of lost carts",
            "AI Product Recommendation Engine — shows personalized upsells that increase AOV by 15-30%",
            "AI Customer Segmentation — identifies high-value customers for VIP treatment",
            "AI Inventory-Based Promotions — automatically promotes low-stock items and clears overstock",
        ],
    },
    "local business": {
        "critical_signals": ["gmb_profile", "reviews", "local_seo", "contact_accessibility", "trust_signals"],
        "must_have": ["complete GMB profile", "10+ reviews", "clear contact info", "service area defined"],
        "nice_to_have": ["blog", "FAQ", "social presence", "booking system"],
        "biggest_killers": ["incomplete GMB", "no reviews", "not in local pack"],
        "avg_customer_value": 350,
        "avg_visits_per_customer_year": 2,
        "key_benchmarks": {
            "avg_google_reviews": 39,
            "local_pack_click_share": 44,
        },
        "ai_opportunities": [
            "AI Local SEO System — optimizes GMB and builds local citation network",
            "AI Review Generation Engine — systematic post-service review collection",
            "AI Lead Capture Bot — converts website visitors to leads 24/7",
            "AI Follow-up Sequences — automated nurture for unconverted leads",
        ],
    },
}


class IndustryAnalyzer:
    def __init__(self, business_type: str, audit_data: dict):
        self.business_type = business_type.lower()
        self.audit_data = audit_data
        self.profile = self._get_profile()

    def _get_profile(self) -> dict:
        for key in INDUSTRY_PROFILES:
            if key in self.business_type or self.business_type in key:
                return INDUSTRY_PROFILES[key]
        return INDUSTRY_PROFILES["local business"]

    def analyze(self) -> dict:
        missing = self._check_must_haves()
        score = self._industry_score(missing)
        opportunities = self._top_ai_opportunities()
        revenue = self._revenue_model()

        return {
            "industry": self.business_type,
            "profile_matched": self.profile is not INDUSTRY_PROFILES["local business"],
            "must_have_missing": missing,
            "industry_score": score,
            "critical_signals": self.profile.get("critical_signals", []),
            "biggest_killers": self.profile.get("biggest_killers", []),
            "top_ai_opportunities": opportunities,
            "revenue_model": revenue,
            "avg_customer_value": self.profile.get("avg_customer_value", 350),
            "key_benchmarks": self.profile.get("key_benchmarks", {}),
        }

    def _check_must_haves(self) -> list:
        must_haves = self.profile.get("must_have", [])
        missing = []

        site = self.audit_data.get("website", {})
        conv = site.get("conversion_signals", {})
        trust = site.get("trust_signals", {})
        reviews = self.audit_data.get("reviews", {}).get("assessment", {})
        seo = self.audit_data.get("seo", {})

        for item in must_haves:
            item_lower = item.lower()
            is_missing = False

            if "review" in item_lower:
                count = reviews.get("google_review_count") or 0
                benchmark = self.profile.get("key_benchmarks", {}).get("avg_google_reviews", 20)
                is_missing = count < benchmark * 0.4
            elif "booking" in item_lower or "appointment" in item_lower:
                is_missing = not conv.get("booking_system")
            elif "blog" in item_lower or "content" in item_lower:
                is_missing = not site.get("content_signals", {}).get("has_blog")
            elif "contact" in item_lower or "phone" in item_lower:
                is_missing = not trust.get("has_phone_number")
            elif "schema" in item_lower or "gmb" in item_lower:
                is_missing = not seo.get("local_seo", {}).get("has_local_business_schema")
            elif "consultation" in item_lower or "free offer" in item_lower:
                is_missing = not conv.get("has_free_offer")
            elif "guarantee" in item_lower:
                is_missing = not site.get("global_signals", {}).get("has_guarantee")
            elif "faq" in item_lower:
                is_missing = not site.get("homepage", {}).get("has_faq")

            if is_missing:
                missing.append(item)

        return missing

    def _industry_score(self, missing: list) -> dict:
        must_have_count = len(self.profile.get("must_have", []))
        missing_count = len(missing)
        score = round(((must_have_count - missing_count) / max(must_have_count, 1)) * 100)

        return {
            "score": score,
            "grade": "Strong" if score >= 80 else "Moderate" if score >= 60 else "Weak",
            "must_haves_missing": missing_count,
            "must_haves_total": must_have_count,
        }

    def _top_ai_opportunities(self) -> list:
        return self.profile.get("ai_opportunities", [])[:4]

    def _revenue_model(self) -> dict:
        acv = self.profile.get("avg_customer_value", 350)
        visits_per_year = self.profile.get("avg_visits_per_customer_year", 2)
        monthly_visitors = self.audit_data.get("traffic", {}).get("estimated_monthly_visitors", 500)
        current_conversion = 0.025
        optimized_conversion = 0.06

        current_leads = round(monthly_visitors * current_conversion)
        optimized_leads = round(monthly_visitors * optimized_conversion)
        monthly_gap = optimized_leads - current_leads
        annual_revenue_gap = round(monthly_gap * acv * visits_per_year)

        return {
            "avg_customer_value": acv,
            "estimated_current_monthly_leads": current_leads,
            "estimated_optimized_monthly_leads": optimized_leads,
            "monthly_leads_gap": monthly_gap,
            "annual_revenue_opportunity": annual_revenue_gap,
            "monthly_revenue_opportunity": round(annual_revenue_gap / 12),
        }
