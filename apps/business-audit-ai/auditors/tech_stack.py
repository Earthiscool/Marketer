"""
Tech Stack Auditor — detects 60+ tools from HTML, headers, scripts, and cookies.
No API key needed. Analyzes: CMS, email marketing, CRM, chat, analytics, ads,
booking, payments, reviews, A/B testing, heatmaps.

Knowing their stack reveals gaps: using Mailchimp but no automation,
has Stripe but no cart recovery, WordPress but no SEO plugin, etc.
"""
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Each entry: { "name": display name, "category": category, "signals": [patterns to match in HTML/headers] }
TECH_SIGNATURES = {
    # CMS
    "WordPress": {"category": "CMS", "signals": ["wp-content", "wp-includes", "wordpress", "/wp-json/"]},
    "Shopify": {"category": "CMS / E-commerce", "signals": ["cdn.shopify.com", "shopify.com/s/files", "Shopify.theme"]},
    "Wix": {"category": "CMS", "signals": ["wix.com", "wixsite.com", "X-Wix-", "wix-bolt"]},
    "Squarespace": {"category": "CMS", "signals": ["squarespace.com", "sqsp.net", "squarespace-cdn"]},
    "Webflow": {"category": "CMS", "signals": ["webflow.com", "webflow.io", "Webflow:"]},
    "Ghost": {"category": "CMS", "signals": ["ghost.org", "ghost-", "Ghost "]},
    "Drupal": {"category": "CMS", "signals": ["drupal.org", "Drupal.settings", "/sites/default/files/"]},
    "Joomla": {"category": "CMS", "signals": ["joomla!", "/components/com_", "Joomla!"]},
    "HubSpot CMS": {"category": "CMS", "signals": ["hs-scripts.com", "hubspot.net/cms", "hscta-"]},
    "BigCommerce": {"category": "CMS / E-commerce", "signals": ["bigcommerce.com", "bc-sf-filter"]},
    "Magento": {"category": "CMS / E-commerce", "signals": ["mage/cookies", "Magento_", "var BLANK_URL"]},
    "WooCommerce": {"category": "E-commerce", "signals": ["woocommerce", "wc-ajax", "add-to-cart"]},

    # Analytics
    "Google Analytics 4": {"category": "Analytics", "signals": ["gtag('config'", "G-", "googletagmanager.com/gtag"]},
    "Google Tag Manager": {"category": "Analytics", "signals": ["googletagmanager.com/gtm.js", "GTM-"]},
    "Mixpanel": {"category": "Analytics", "signals": ["mixpanel.com/lib", "mixpanel.track"]},
    "Amplitude": {"category": "Analytics", "signals": ["amplitude.com/libs", "amplitude.getInstance"]},
    "Hotjar": {"category": "Analytics / Heatmaps", "signals": ["static.hotjar.com", "hjid", "hotjar"]},
    "Microsoft Clarity": {"category": "Analytics / Heatmaps", "signals": ["clarity.ms", "microsoft/clarity"]},
    "FullStory": {"category": "Analytics / Heatmaps", "signals": ["fullstory.com/s/fs.js", "FS.identify"]},
    "Heap": {"category": "Analytics", "signals": ["heapanalytics.com", "heap.load"]},

    # Advertising / Pixels
    "Facebook Pixel": {"category": "Advertising", "signals": ["connect.facebook.net/en_US/fbevents.js", "fbq('init'", "_fbp"]},
    "Google Ads": {"category": "Advertising", "signals": ["googleadservices.com", "AW-", "gtag('event', 'conversion'"]},
    "LinkedIn Insight": {"category": "Advertising", "signals": ["snap.licdn.com", "linkedin.com/insight", "_linkedin_partner_id"]},
    "TikTok Pixel": {"category": "Advertising", "signals": ["analytics.tiktok.com", "ttq.load"]},
    "Pinterest Tag": {"category": "Advertising", "signals": ["pintrk('load'", "ct.pinterest.com"]},
    "Twitter/X Pixel": {"category": "Advertising", "signals": ["static.ads-twitter.com", "twq('init'"]},

    # Email Marketing
    "Mailchimp": {"category": "Email Marketing", "signals": ["mailchimp.com", "list-manage.com", "mc.us"]},
    "Klaviyo": {"category": "Email Marketing", "signals": ["klaviyo.com", "klaviyo_account_", "KlaviyoSubscribe"]},
    "ActiveCampaign": {"category": "Email Marketing", "signals": ["activehosted.com", "activecampaign.com"]},
    "HubSpot Email": {"category": "Email Marketing / CRM", "signals": ["hs-scripts.com", "hsforms.com", "_hsq"]},
    "Constant Contact": {"category": "Email Marketing", "signals": ["constantcontact.com", "r20.rs6.net"]},
    "ConvertKit": {"category": "Email Marketing", "signals": ["convertkit.com", "ck.page"]},
    "Drip": {"category": "Email Marketing", "signals": ["getdrip.com", "drip.com/e"]},
    "Brevo / Sendinblue": {"category": "Email Marketing", "signals": ["sibforms.com", "sendinblue.com"]},

    # CRM
    "Salesforce": {"category": "CRM", "signals": ["salesforce.com", "force.com", "Salesforce.com"]},
    "HubSpot CRM": {"category": "CRM", "signals": ["hs-analytics.net", "hubspot.com/crm"]},
    "Zoho CRM": {"category": "CRM", "signals": ["zoho.com", "zohocrm"]},
    "Pipedrive": {"category": "CRM", "signals": ["pipedrive.com", "cdn.pipedrive.com"]},

    # Chat / Support
    "Intercom": {"category": "Chat", "signals": ["intercom.io", "widget.intercom.io", "intercomSettings"]},
    "Drift": {"category": "Chat", "signals": ["drift.com", "js.driftt.com", "driftt.com"]},
    "Zendesk": {"category": "Chat", "signals": ["zendesk.com", "zopim.com", "zdassets.com"]},
    "Tidio": {"category": "Chat", "signals": ["tidiochat.com", "tidio.co"]},
    "LiveChat": {"category": "Chat", "signals": ["livechatinc.com", "cdn.livechatinc.com"]},
    "Crisp": {"category": "Chat", "signals": ["crisp.chat", "client.crisp.chat"]},
    "Tawk.to": {"category": "Chat", "signals": ["tawk.to", "embed.tawk.to"]},
    "HubSpot Chat": {"category": "Chat", "signals": ["js.usemessages.com", "HubSpotConversations"]},

    # Booking / Scheduling
    "Calendly": {"category": "Booking", "signals": ["calendly.com", "assets.calendly.com"]},
    "Acuity Scheduling": {"category": "Booking", "signals": ["acuityscheduling.com", "squareup.com/appointments"]},
    "Mindbody": {"category": "Booking", "signals": ["mindbodyonline.com", "widgets.mindbodyonline.com"]},
    "OpenTable": {"category": "Booking", "signals": ["opentable.com", "ot-widget"]},
    "Booksy": {"category": "Booking", "signals": ["booksy.com", "widget.booksy.com"]},
    "Vagaro": {"category": "Booking", "signals": ["vagaro.com"]},
    "Fresha": {"category": "Booking", "signals": ["fresha.com", "widget.fresha.com"]},

    # Payments
    "Stripe": {"category": "Payments", "signals": ["js.stripe.com", "stripe.com/v3", "Stripe("]},
    "PayPal": {"category": "Payments", "signals": ["paypal.com/sdk/js", "paypal.Buttons"]},
    "Square": {"category": "Payments", "signals": ["squareup.com/payments", "cashapp.com"]},
    "Klarna": {"category": "Payments", "signals": ["klarna.com", "x.klarnacdn.net"]},
    "Afterpay": {"category": "Payments", "signals": ["afterpay.com", "js.afterpay.com"]},

    # Reviews / Social Proof
    "Trustpilot": {"category": "Reviews", "signals": ["trustpilot.com", "widget.trustpilot.com"]},
    "Yotpo": {"category": "Reviews", "signals": ["yotpo.com", "staticw2.yotpo.com"]},
    "Birdeye": {"category": "Reviews", "signals": ["birdeye.com", "birdeye.widget"]},
    "Podium": {"category": "Reviews", "signals": ["podium.com", "cdn.podium.com"]},

    # A/B Testing
    "Optimizely": {"category": "A/B Testing", "signals": ["optimizely.com", "cdn.optimizely.com"]},
    "VWO": {"category": "A/B Testing", "signals": ["vwo.com", "visualwebsiteoptimizer.com", "vwoCode"]},
    "Google Optimize": {"category": "A/B Testing", "signals": ["optimize.google.com", "GTM-OPTIMIZE"]},

    # SEO
    "Yoast SEO": {"category": "SEO", "signals": ["yoast.com", "wpseo_", "Yoast SEO"]},
    "Rank Math": {"category": "SEO", "signals": ["rankMath", "rank-math"]},
    "SEMrush": {"category": "SEO", "signals": ["semrush.com", "sem_analytics"]},

    # Misc
    "Cloudflare": {"category": "CDN / Security", "signals": ["cloudflare.com", "__cflb", "cf-ray", "cloudflare"]},
    "reCAPTCHA": {"category": "Security", "signals": ["recaptcha/api.js", "g-recaptcha"]},
    "Typeform": {"category": "Forms", "signals": ["typeform.com", "embed.typeform.com"]},
    "JotForm": {"category": "Forms", "signals": ["jotform.com", "form.jotform"]},
}

# What gaps in the stack mean (for cold email angles)
STACK_GAP_ANGLES = {
    "Email Marketing": "No email marketing detected — they're losing repeat business with no follow-up system",
    "Chat": "No live chat tool — leads landing on site with questions bounce instead of converting",
    "Analytics": "No analytics beyond basic tracking — flying blind on what's working",
    "Booking": "No online booking system — requiring phone calls loses 40% of after-hours leads",
    "CRM": "No CRM detected — customer data likely in spreadsheets or owner's head",
    "Advertising": "No ad pixels — can't retarget visitors or build lookalike audiences",
    "A/B Testing": "No A/B testing — never optimizing conversion rate",
    "Reviews": "No review widget — social proof not being leveraged on site",
}


class TechStackAuditor:
    def __init__(self, url: str, website_data: dict = None):
        self.url = url
        self.website_data = website_data or {}

    def audit(self) -> dict:
        html, headers_raw = self._fetch_page()
        detected = self._detect_tools(html, headers_raw)
        categories = self._group_by_category(detected)
        gaps = self._identify_gaps(categories)
        sophistication = self._score_sophistication(detected, gaps)

        return {
            "tools_detected": detected,
            "tool_count": len(detected),
            "categories": categories,
            "gaps": gaps,
            "sophistication_score": sophistication,
            "insights": self._generate_insights(detected, gaps, sophistication),
        }

    def _fetch_page(self):
        try:
            r = requests.get(self.url, headers=HEADERS, timeout=10)
            return r.text, dict(r.headers)
        except Exception:
            # Use cached website data if available
            return self.website_data.get("raw_html", ""), {}

    def _detect_tools(self, html: str, response_headers: dict) -> list:
        detected = []
        html_lower = html.lower()
        headers_str = " ".join(f"{k}: {v}" for k, v in response_headers.items()).lower()
        combined = html_lower + " " + headers_str

        for tool_name, config in TECH_SIGNATURES.items():
            for signal in config["signals"]:
                if signal.lower() in combined:
                    detected.append({
                        "name": tool_name,
                        "category": config["category"],
                        "signal_matched": signal,
                    })
                    break

        return detected

    def _group_by_category(self, detected: list) -> dict:
        categories = {}
        for tool in detected:
            cat = tool["category"].split(" / ")[0]  # normalize
            categories.setdefault(cat, []).append(tool["name"])
        return categories

    def _identify_gaps(self, categories: dict) -> list:
        gaps = []
        for cat, angle in STACK_GAP_ANGLES.items():
            if cat not in categories:
                gaps.append({
                    "missing_category": cat,
                    "cold_email_angle": angle,
                })
        return gaps

    def _score_sophistication(self, detected: list, gaps: list) -> dict:
        tool_count = len(detected)
        gap_count = len(gaps)

        # Weighted scoring: some tools matter more
        high_value = {"Analytics", "Email Marketing", "CRM", "Advertising"}
        categories_present = {t["category"].split(" / ")[0] for t in detected}
        high_value_score = len(high_value & categories_present)

        score = min(100, tool_count * 6 + high_value_score * 10)

        return {
            "score": score,
            "tool_count": tool_count,
            "grade": "Advanced" if score >= 70 else "Intermediate" if score >= 40 else "Basic",
            "high_value_tools_present": high_value_score,
            "missing_critical_categories": gap_count,
        }

    def _generate_insights(self, detected: list, gaps: list, sophistication: dict) -> list:
        insights = []
        grade = sophistication.get("grade", "Basic")

        if grade == "Basic":
            insights.append({
                "type": "tech_sophistication",
                "finding": f"Only {sophistication['tool_count']} marketing/sales tools detected — severely underpowered stack",
                "impact": "Missing the infrastructure needed to capture, nurture, and convert leads automatically",
                "urgency": "high",
            })

        for gap in gaps[:3]:
            insights.append({
                "type": "tech_gap",
                "finding": f"No {gap['missing_category']} tool detected",
                "impact": gap["cold_email_angle"],
                "urgency": "high" if gap["missing_category"] in {"Email Marketing", "Chat", "Analytics"} else "medium",
            })

        # Positive signals
        chat_tools = [t["name"] for t in detected if "Chat" in t["category"]]
        if chat_tools:
            insights.append({
                "type": "tech_positive",
                "finding": f"Uses {chat_tools[0]} for live chat — good lead capture signal",
                "impact": "Already investing in conversion tools",
                "urgency": "low",
            })

        return insights
