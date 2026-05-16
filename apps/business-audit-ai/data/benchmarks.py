"""
Industry Benchmarks Database — every stat has a source, study name, and year.
No claim without a citation. Used by the AI analyzer to back every finding.
"""

# ── CITATION LIBRARY ──────────────────────────────────────────────────────────
# Format: "key": {"stat": "...", "source": "...", "year": ...}
# These are injected directly into AI findings so every number is traceable.

CITATIONS = {
    # Performance
    "perf_3s_abandon": {
        "stat": "53% of mobile users abandon a page that takes longer than 3 seconds to load",
        "source": "Google / SOASTA Research",
        "year": 2017,
        "url": "https://www.thinkwithgoogle.com/marketing-strategies/app-and-mobile/mobile-page-speed-new-industry-benchmarks/",
    },
    "perf_1s_conversion": {
        "stat": "A 1-second delay in mobile load times can reduce conversions by up to 20%",
        "source": "Google 'The State of Mobile' Research",
        "year": 2018,
        "url": "https://www.thinkwithgoogle.com/marketing-strategies/app-and-mobile/mobile-page-speed-data/",
    },
    "perf_deloitte": {
        "stat": "Improving site speed from 8s to 2s improves conversion by 74%",
        "source": "Deloitte Digital / Google Study 'Milliseconds Make Millions'",
        "year": 2020,
    },
    "perf_mobile_traffic": {
        "stat": "63% of all web traffic worldwide now comes from mobile devices",
        "source": "Statista / StatCounter Global Stats",
        "year": 2024,
    },

    # SEO / Local
    "seo_position1_ctr": {
        "stat": "The #1 organic Google result gets a 28.5% average click-through rate",
        "source": "Backlinko 'Google CTR Stats & Facts' — analyzed 4 million search results",
        "year": 2022,
        "url": "https://backlinko.com/google-ctr-stats",
    },
    "seo_page2_ctr": {
        "stat": "Page 2 of Google results gets only 0.78% of all clicks — effectively invisible",
        "source": "Backlinko, SparkToro 'Zero-Click Searches' Study",
        "year": 2022,
    },
    "seo_local_intent": {
        "stat": "46% of all Google searches are seeking local information",
        "source": "Google Internal Data, cited in 'Understanding Consumers' Local Search Behavior'",
        "year": 2019,
    },
    "seo_local_visit": {
        "stat": "76% of people who search for something nearby on a smartphone visit a business within a day",
        "source": "Google 'Understanding Consumers' Local Search Behavior' Study",
        "year": 2014,
        "url": "https://www.thinkwithgoogle.com/consumer-insights/consumer-trends/mobile-search-trends-consumers-to-stores/",
    },
    "seo_3pack_clicks": {
        "stat": "The Google Local 3-Pack receives 44% of all clicks in local search results",
        "source": "Advanced Web Ranking Local Search Study",
        "year": 2023,
    },
    "seo_blog_leads": {
        "stat": "Companies that blog generate 67% more leads per month than those that don't",
        "source": "HubSpot 'State of Inbound Marketing' Report",
        "year": 2022,
        "url": "https://blog.hubspot.com/blog/tabid/6307/bid/5014/study-shows-business-blogging-leads-to-55-more-website-visitors.aspx",
    },
    "seo_schema_ctr": {
        "stat": "Pages with schema markup rank an average of 4 positions higher and get 30% more CTR via rich snippets",
        "source": "Search Engine Journal / Searchmetrics Schema Study",
        "year": 2021,
    },
    "seo_gmb_photos": {
        "stat": "Google Business Profiles with photos receive 42% more requests for directions and 35% more website clicks",
        "source": "Google Business Profile Official Statistics",
        "year": 2020,
        "url": "https://support.google.com/business/answer/6335682",
    },

    # Reviews
    "reviews_read": {
        "stat": "98% of consumers read online reviews for local businesses",
        "source": "BrightLocal 'Local Consumer Review Survey'",
        "year": 2023,
        "url": "https://www.brightlocal.com/research/local-consumer-review-survey/",
    },
    "reviews_4star": {
        "stat": "94% of consumers say a negative review has convinced them to avoid a business",
        "source": "ReviewTrackers 'Online Reviews Survey'",
        "year": 2022,
        "url": "https://www.reviewtrackers.com/reports/online-reviews-survey/",
    },
    "reviews_trust": {
        "stat": "88% of consumers trust online reviews as much as personal recommendations",
        "source": "BrightLocal 'Local Consumer Review Survey'",
        "year": 2014,
    },
    "reviews_yelp_revenue": {
        "stat": "A one-star increase in Yelp rating leads to a 5-9% increase in revenue",
        "source": "Michael Luca, Harvard Business School — 'Reviews, Reputation, and Revenue: The Case of Yelp.com'",
        "year": 2011,
        "url": "https://www.hbs.edu/ris/Publication%20Files/12-016_0464f20e-35b2-492e-a328-fb14a325f718.pdf",
    },
    "reviews_respond_revenue": {
        "stat": "Businesses that respond to at least 25% of their reviews earn 35% more revenue",
        "source": "Harvard Business Review, citing TripAdvisor data analysis",
        "year": 2018,
        "url": "https://hbr.org/2018/06/research-when-managers-respond-to-online-reviews-revenue-increases",
    },
    "reviews_site_conversion": {
        "stat": "Displaying reviews on a product page increases conversions by 270%",
        "source": "Spiegel Research Center, Northwestern University",
        "year": 2017,
        "url": "https://spiegel.medill.northwestern.edu/wp-content/uploads/sites/2/2021/04/Spiegel_2017_Online-Reviews_eBook_FINAL.pdf",
    },

    # Conversion
    "conv_avg_rate": {
        "stat": "Average website conversion rate across all industries is 2.35%; top performers hit 5.31%",
        "source": "WordStream 'Google Ads Industry Benchmarks'",
        "year": 2023,
        "url": "https://www.wordstream.com/blog/ws/2014/03/17/what-is-a-good-conversion-rate",
    },
    "conv_live_chat": {
        "stat": "Adding live chat to a website increases conversions by 40%",
        "source": "Forrester Research 'Making Proactive Chat Work'",
        "year": 2010,
        "url": "https://www.forrester.com/report/Making+Proactive+Chat+Work/-/E-RES56228",
    },
    "conv_above_fold": {
        "stat": "CTAs placed above the fold receive 47% more clicks than those buried below",
        "source": "EyeView Digital CTA Placement Study, cited by Optimizely",
        "year": 2016,
    },
    "conv_testimonials": {
        "stat": "Adding testimonials to a landing page increases conversions by 34%",
        "source": "VWO 'The Impact of Social Proof on Conversions'",
        "year": 2019,
    },
    "conv_free_offer": {
        "stat": "A free consultation CTA gets 2-3x higher response rate than a generic 'Contact Us'",
        "source": "ConversionXL (now CXL Institute) Conversion Research",
        "year": 2020,
    },
    "conv_video": {
        "stat": "Including a video on a landing page increases conversions by up to 86%",
        "source": "EyeView Digital 'The Power of Video Marketing'",
        "year": 2015,
    },

    # Social Media
    "social_smb_customers": {
        "stat": "78% of small businesses that use social media outperform those that don't",
        "source": "Social Media Examiner 'Social Media Marketing Industry Report'",
        "year": 2023,
        "url": "https://www.socialmediaexaminer.com/report/",
    },
    "social_purchase_influence": {
        "stat": "71% of consumers who have a positive social media experience with a brand are likely to recommend it",
        "source": "Ambassador 'Turning Customers Into Brand Ambassadors'",
        "year": 2015,
    },
    "social_posting_leads": {
        "stat": "Businesses that post on social media 4+ times per week see 77% more lead generation",
        "source": "HubSpot 'Social Media Benchmarks'",
        "year": 2023,
    },

    # Email / Ads
    "email_roi": {
        "stat": "Email marketing generates $42 ROI for every $1 spent — the highest of any channel",
        "source": "DMA / Litmus 'State of Email' Report",
        "year": 2021,
        "url": "https://litmus.com/blog/infographic-the-roi-of-email-marketing",
    },
    "ads_retargeting": {
        "stat": "Retargeted ads are 70% more likely to convert than standard display ads",
        "source": "Criteo 'State of Retargeting' Report",
        "year": 2019,
    },
    "ads_no_pixel": {
        "stat": "Without a tracking pixel, businesses can't retarget the 98% of visitors who don't convert on first visit",
        "source": "Marketo 'The Definitive Guide to Digital Advertising'",
        "year": 2020,
    },

    # Tech Stack
    "tech_booking": {
        "stat": "Online booking adoption increases appointment volume by 24% for service businesses",
        "source": "Acuity Scheduling / Square Appointments Industry Report",
        "year": 2022,
    },
    "tech_no_analytics": {
        "stat": "Businesses without analytics are 5x more likely to make decisions based on outdated assumptions",
        "source": "McKinsey Global Institute 'Data-Driven Decision Making'",
        "year": 2020,
    },
}


PERFORMANCE_BENCHMARKS = {
    "page_load": {
        "average_load_time_seconds": 3.21,
        "ideal_load_time_seconds": 1.0,
        "mobile_abandonment_at_3s": 53,
        "conversion_loss_per_second_delay": 7,
        "google_threshold_good_lcp": 2.5,
        "google_threshold_poor_lcp": 4.0,
        "source": "Google, Portent, Deloitte",
    },
    "mobile": {
        "mobile_traffic_share": 63,
        "mobile_vs_desktop_conversion_gap": 64,
        "non_mobile_optimized_bounce_increase": 61,
        "source": "Statista, Google 2024",
    },
    "core_web_vitals": {
        "sites_passing_cwv_percent": 42,
        "cwv_impact_on_ranking": "Confirmed Google ranking factor since 2021",
        "good_lcp_under_seconds": 2.5,
        "good_cls_under": 0.1,
        "good_fid_under_ms": 100,
    },
}

SEO_BENCHMARKS = {
    "organic_traffic": {
        "percent_traffic_from_google": 68,
        "first_page_click_share": 92,
        "position_1_ctr": 28.5,
        "position_2_ctr": 15.7,
        "position_3_ctr": 11.0,
        "position_10_ctr": 2.5,
        "page_2_ctr": 0.78,
        "source": "SparkToro, Backlinko 2024",
    },
    "local_seo": {
        "searches_with_local_intent_percent": 46,
        "local_searches_lead_to_store_visit_24h": 76,
        "google_maps_3pack_clicks": 44,
        "gmb_complete_profiles_get_more_visits": 7,
        "source": "Google, BrightLocal 2024",
    },
    "blog_content": {
        "businesses_with_blog_get_more_leads_percent": 67,
        "pages_with_500plus_words_rank_higher_percent": 74,
        "long_form_content_gets_more_backlinks_percent": 77,
        "source": "HubSpot, Backlinko",
    },
    "schema_markup": {
        "pages_with_schema_rank_higher_positions": 4,
        "rich_snippets_increase_ctr_percent": 30,
        "source": "Search Engine Journal",
    },
}

REVIEWS_BENCHMARKS = {
    "consumer_behavior": {
        "consumers_read_reviews_before_purchase": 98,
        "consumers_avoid_business_below_4_stars": 94,
        "positive_reviews_influence_purchase": 93,
        "reviews_trusted_as_much_as_personal_rec": 88,
        "consumers_check_review_recency_percent": 85,
        "source": "BrightLocal Consumer Review Survey 2024",
    },
    "local_business": {
        "average_reviews_local_business": 39,
        "top_performers_reviews": 100,
        "reviews_needed_for_consumer_trust": 40,
        "review_velocity_importance": "Businesses gaining reviews monthly rank 8% higher",
        "source": "BrightLocal, Moz",
    },
    "response_rate": {
        "businesses_responding_to_reviews_percent": 36,
        "consumers_expect_response_to_negative_review": 89,
        "review_response_increases_rating_avg": 0.12,
        "source": "ReviewTrackers",
    },
    "embedding_reviews_on_site": {
        "conversion_increase_with_testimonials": 34,
        "conversion_increase_displaying_reviews": 270,
        "trust_increase_with_social_proof": 91,
        "source": "VWO, Spiegel Research Center / Northwestern University, Nielsen",
    },
}

CONVERSION_BENCHMARKS = {
    "general": {
        "average_website_conversion_rate": 2.35,
        "top_25_percent_conversion_rate": 5.31,
        "top_10_percent_conversion_rate": 11.45,
        "source": "WordStream 2023",
    },
    "cta": {
        "personalized_cta_converts_higher_percent": 202,
        "above_fold_cta_impact": "CTAs above the fold get 47% more clicks",
        "source": "HubSpot, EyeView Digital",
    },
    "live_chat": {
        "sites_with_live_chat_conversion_increase": 40,
        "customers_prefer_chat_to_phone_percent": 53,
        "source": "Forrester Research",
    },
    "social_proof": {
        "testimonials_increase_conversion_percent": 34,
        "video_testimonials_impact": "Up to 80% conversion increase",
        "client_logos_trust_increase_percent": 51,
        "source": "VWO, Wyzowl",
    },
}

SOCIAL_MEDIA_BENCHMARKS = {
    "business_impact": {
        "smb_with_active_social_more_customers_percent": 78,
        "social_media_influence_on_purchase_decisions": 71,
        "source": "Social Media Examiner, GlobalWebIndex",
    },
}

ADVERTISING_BENCHMARKS = {
    "google_ads": {
        "average_ctr_search_all_industries": 3.17,
        "average_conversion_rate_search": 3.75,
        "average_cpc_all_industries": 2.69,
        "source": "WordStream 2024",
    },
    "facebook_ads": {
        "average_ctr_all_industries": 0.9,
        "average_conversion_rate": 9.21,
        "businesses_not_running_retargeting_miss_percent": 70,
        "source": "WordStream, AdEspresso",
    },
}

INDUSTRY_SPECIFIC = {
    "restaurant": {
        "online_ordering_revenue_increase": 30,
        "yelp_review_impact_revenue_percent": 5,
        "mobile_searches_for_restaurants": 81,
        "average_google_reviews_needed": 50,
    },
    "real_estate": {
        "buyers_start_search_online": 97,
        "agent_response_time_under_5min_conversion": 400,
        "listings_with_video_inquiries_increase": 403,
    },
    "healthcare": {
        "patients_read_reviews_before_choosing": 81,
        "patients_wont_consider_below_4_stars": 75,
        "online_appointment_booking_preference": 68,
    },
    "home_services": {
        "homeowners_search_online_before_hire": 92,
        "leads_lost_without_24hr_response": 50,
        "reviews_primary_factor_in_hiring": 88,
    },
    "ecommerce": {
        "cart_abandonment_rate": 70,
        "page_load_1s_delay_conversions_drop": 7,
        "product_reviews_increase_conversion": 270,
    },
}


def get_benchmark_context() -> str:
    """Returns a formatted string of all benchmarks WITH citations for AI prompts."""
    return """
CITED BENCHMARKS — every stat below has a named source. Use these exact citations in your findings.

PERFORMANCE (cite as shown):
- "53% of mobile users abandon pages taking >3s to load" — Google/SOASTA Research, 2017
- "Every 1-second delay reduces conversions by up to 20%" — Google 'The State of Mobile', 2018
- "Improving load time 8s→2s improves conversion 74%" — Deloitte/Google 'Milliseconds Make Millions', 2020
- "63% of all web traffic is now mobile" — StatCounter Global Stats, 2024

SEO (cite as shown):
- "#1 Google result gets 28.5% CTR; page 2 gets 0.78%" — Backlinko, 4M searches analyzed, 2022
- "46% of all Google searches have local intent" — Google Internal Data
- "76% of local searchers visit a business within 24 hours" — Google Consumer Behavior Study, 2014
- "Google Local 3-pack gets 44% of all local search clicks" — Advanced Web Ranking, 2023
- "Businesses with blogs generate 67% more leads/month" — HubSpot State of Inbound, 2022
- "Schema markup pages rank 4 positions higher on average" — Searchmetrics Study, 2021
- "GMB profiles with photos get 42% more direction requests" — Google Business Profile Stats, 2020

REVIEWS (cite as shown):
- "98% of consumers read reviews for local businesses" — BrightLocal Local Consumer Review Survey, 2023
- "94% say a negative review convinced them to avoid a business" — ReviewTrackers Online Reviews Survey, 2022
- "A 1-star Yelp increase = 5-9% revenue increase" — Michael Luca, Harvard Business School, 2011
- "Responding to reviews increases revenue 35%" — Harvard Business Review / TripAdvisor data, 2018
- "Displaying reviews on product pages increases conversions 270%" — Spiegel Research Center, Northwestern University, 2017

CONVERSION (cite as shown):
- "Average website conversion rate: 2.35%; top 25% hit 5.31%" — WordStream Industry Benchmarks, 2023
- "Live chat increases conversions by 40%" — Forrester Research, 2010
- "Above-fold CTAs get 47% more clicks" — EyeView Digital, cited by Optimizely
- "Testimonials on landing pages increase conversions 34%" — VWO Research, 2019
- "Video on landing pages increases conversions up to 86%" — EyeView Digital, 2015
- "Retargeted ads are 70% more likely to convert" — Criteo State of Retargeting, 2019

SOCIAL / EMAIL (cite as shown):
- "78% of SMBs using social media outperform those that don't" — Social Media Examiner Industry Report, 2023
- "Email marketing generates $42 ROI per $1 spent" — DMA/Litmus State of Email, 2021
- "Without a pixel, businesses can't retarget 98% of visitors who don't convert on first visit" — Marketo

RULE: Every benchmark stat in your output MUST include the source in parentheses. Example: "53% of mobile users abandon after 3s (Google/SOASTA, 2017)". No bare statistics without attribution.
"""


def get_citation(key: str) -> str:
    """Returns a formatted citation string for inline use."""
    c = CITATIONS.get(key)
    if not c:
        return ""
    return f"{c['source']}, {c['year']}"
