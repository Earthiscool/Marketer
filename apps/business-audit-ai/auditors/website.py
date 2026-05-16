"""
Website Auditor — scrapes and deeply analyzes every aspect of a business website.
Looks at content quality, trust signals, conversion elements, UX, and more.
"""
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class WebsiteAuditor:
    def __init__(self, url: str):
        self.base_url = url.rstrip("/")
        self.domain = urlparse(url).netloc
        self.pages_visited = {}
        self.all_links = set()
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        try:
            r = self._session.get(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
        except Exception:
            pass
        return None

    def audit(self) -> dict:
        soup = self.fetch(self.base_url)
        if not soup:
            return {"error": "Could not fetch website"}

        result = {
            "homepage": self._analyze_page(soup, self.base_url),
            "internal_pages": {},
            "global_signals": {},
            "trust_signals": {},
            "conversion_signals": {},
            "content_signals": {},
            "technical_signals": {},
            "navigation": {},
        }

        # Discover and visit key internal pages
        key_pages = self._find_key_pages(soup)
        for label, page_url in key_pages.items():
            page_soup = self.fetch(page_url)
            if page_soup:
                result["internal_pages"][label] = self._analyze_page(page_soup, page_url)

        result["global_signals"] = self._global_signals(soup, key_pages)
        result["trust_signals"] = self._trust_signals(soup, result["internal_pages"])
        result["conversion_signals"] = self._conversion_signals(soup, result["internal_pages"])
        result["content_signals"] = self._content_signals(soup, result["internal_pages"])
        result["technical_signals"] = self._technical_signals(soup)
        result["navigation"] = self._navigation_signals(soup)

        return result

    def _analyze_page(self, soup: BeautifulSoup, url: str) -> dict:
        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())

        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

        return {
            "url": url,
            "title": soup.title.string.strip() if soup.title else None,
            "meta_description": meta_desc,
            "word_count": word_count,
            "h1_tags": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "h2_tags": [h.get_text(strip=True) for h in soup.find_all("h2")],
            "h3_tags": [h.get_text(strip=True) for h in soup.find_all("h3")],
            "has_video": bool(soup.find_all(["video", "iframe"])),
            "image_count": len(soup.find_all("img")),
            "images_missing_alt": len([i for i in soup.find_all("img") if not i.get("alt")]),
            "has_cta_buttons": self._detect_ctas(soup),
            "forms": self._analyze_forms(soup),
            "phone_numbers": self._extract_phones(text),
            "email_addresses": self._extract_emails(text),
            "has_pricing": self._has_pricing(text),
            "has_testimonials": self._has_testimonials(soup),
            "has_faq": self._has_faq(soup, text),
            "has_blog_content": self._has_blog(soup, url),
            "outbound_links": self._outbound_links(soup),
            "internal_link_count": self._internal_link_count(soup),
            "schema_markup": self._check_schema(soup),
            "text_preview": text[:500],
        }

    def _find_key_pages(self, soup: BeautifulSoup) -> dict:
        key_pages = {}
        keywords = {
            "about": ["about", "about-us", "about_us", "our-story", "who-we-are"],
            "services": ["services", "service", "what-we-do", "solutions", "offerings"],
            "contact": ["contact", "contact-us", "get-in-touch", "reach-us"],
            "pricing": ["pricing", "price", "plans", "packages", "rates"],
            "blog": ["blog", "news", "articles", "insights", "resources"],
            "testimonials": ["testimonials", "reviews", "success-stories", "case-studies"],
            "faq": ["faq", "faqs", "frequently-asked", "questions"],
        }

        all_links = soup.find_all("a", href=True)
        for link in all_links:
            href = link["href"].lower().strip("/")
            full_url = urljoin(self.base_url, link["href"])
            parsed = urlparse(full_url)
            if parsed.netloc != self.domain and self.domain not in parsed.netloc:
                continue
            for label, patterns in keywords.items():
                if label not in key_pages:
                    for pat in patterns:
                        if pat in href:
                            key_pages[label] = full_url
                            break

        return key_pages

    def _detect_ctas(self, soup: BeautifulSoup) -> dict:
        cta_keywords = ["get started", "book", "schedule", "call us", "contact", "buy now",
                        "sign up", "free", "quote", "demo", "learn more", "try", "start"]
        buttons = soup.find_all(["button", "a"])
        found_ctas = []
        for btn in buttons:
            text = btn.get_text(strip=True).lower()
            for kw in cta_keywords:
                if kw in text:
                    found_ctas.append(btn.get_text(strip=True))
                    break

        above_fold_cta = False
        hero = soup.find(class_=re.compile(r"hero|banner|header|above|fold", re.I))
        if hero:
            hero_text = hero.get_text().lower()
            above_fold_cta = any(kw in hero_text for kw in cta_keywords)

        return {
            "count": len(found_ctas),
            "examples": found_ctas[:5],
            "above_fold_cta": above_fold_cta,
        }

    def _analyze_forms(self, soup: BeautifulSoup) -> dict:
        forms = soup.find_all("form")
        form_data = []
        for form in forms:
            inputs = form.find_all(["input", "textarea", "select"])
            visible_inputs = [i for i in inputs if i.get("type") not in ["hidden", "submit"]]
            submit_btn = form.find(["button", "input"], {"type": ["submit", "button"]})
            form_data.append({
                "field_count": len(visible_inputs),
                "field_names": [i.get("name", i.get("placeholder", "unknown")) for i in visible_inputs],
                "has_submit": bool(submit_btn),
                "submit_text": submit_btn.get_text(strip=True) if submit_btn else None,
                "has_phone_field": any("phone" in str(i).lower() or "tel" in str(i).lower() for i in visible_inputs),
                "has_email_field": any("email" in str(i).lower() for i in visible_inputs),
            })
        return {"count": len(forms), "forms": form_data}

    def _extract_phones(self, text: str) -> list:
        pattern = r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]"
        return list(set(re.findall(pattern, text)))[:3]

    def _extract_emails(self, text: str) -> list:
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return list(set(re.findall(pattern, text)))[:3]

    def _has_pricing(self, text: str) -> bool:
        patterns = [r"\$\d+", r"pricing", r"per month", r"per year", r"/mo", r"starting at", r"plans?"]
        return any(re.search(p, text, re.I) for p in patterns)

    def _has_testimonials(self, soup: BeautifulSoup) -> dict:
        indicators = ["testimonial", "review", "what our clients say", "what people say",
                      "customer stories", "client feedback", "stars"]
        text = soup.get_text().lower()
        found = [i for i in indicators if i in text]
        star_ratings = soup.find_all(class_=re.compile(r"star|rating|review", re.I))
        quote_blocks = soup.find_all(["blockquote", "q"])
        return {
            "has_testimonials": bool(found or quote_blocks),
            "indicators_found": found,
            "quote_count": len(quote_blocks),
            "star_rating_elements": len(star_ratings),
        }

    def _has_faq(self, soup: BeautifulSoup, text: str) -> bool:
        faq_indicators = ["frequently asked", "faq", "common questions", "people ask"]
        return any(ind in text.lower() for ind in faq_indicators)

    def _has_blog(self, soup: BeautifulSoup, url: str) -> bool:
        blog_indicators = ["blog", "article", "post", "news", "insight"]
        return any(ind in url.lower() for ind in blog_indicators) or \
               bool(soup.find(class_=re.compile(r"blog|article|post", re.I)))

    def _outbound_links(self, soup: BeautifulSoup) -> list:
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and self.domain not in href:
                links.append(href)
        return links[:10]

    def _internal_link_count(self, soup: BeautifulSoup) -> int:
        count = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http") or self.domain in href:
                count += 1
        return count

    def _check_schema(self, soup: BeautifulSoup) -> dict:
        schemas = soup.find_all("script", {"type": "application/ld+json"})
        schema_types = []
        for s in schemas:
            try:
                data = json.loads(s.string)
                schema_type = data.get("@type", "unknown") if isinstance(data, dict) else "list"
                schema_types.append(schema_type)
            except Exception:
                pass
        return {
            "has_schema": bool(schemas),
            "schema_types": schema_types,
            "has_local_business": "LocalBusiness" in str(schema_types),
            "has_organization": "Organization" in str(schema_types),
            "has_faq_schema": "FAQPage" in str(schema_types),
            "has_review_schema": "Review" in str(schema_types) or "AggregateRating" in str(schema_types),
        }

    def _global_signals(self, soup: BeautifulSoup, key_pages: dict) -> dict:
        text = soup.get_text().lower()
        return {
            "pages_found": list(key_pages.keys()),
            "missing_key_pages": [p for p in ["about", "services", "contact", "pricing"] if p not in key_pages],
            "has_live_chat": bool(soup.find_all(class_=re.compile(r"chat|intercom|drift|crisp|tawk", re.I))) or
                            "intercom" in str(soup).lower() or "drift" in str(soup).lower() or
                            "tawk" in str(soup).lower() or "crisp" in str(soup).lower(),
            "has_cookie_banner": bool(soup.find_all(class_=re.compile(r"cookie|gdpr|consent", re.I))),
            "has_ssl_indicators": "https" in self.base_url,
            "has_guarantee": any(w in text for w in ["guarantee", "money back", "satisfaction", "risk free"]),
            "has_awards_badges": any(w in text for w in ["award", "certified", "accredited", "recognized", "badge"]),
            "has_press_mentions": any(w in text for w in ["featured in", "as seen in", "press", "media"]),
            "has_video_content": bool(soup.find_all(["video", "iframe"])),
            "popup_detected": bool(soup.find_all(class_=re.compile(r"popup|modal|overlay|lightbox", re.I))),
            "exit_intent_detected": "exitintent" in str(soup).lower() or "exit-intent" in str(soup).lower(),
            "has_newsletter_signup": any(w in text for w in ["newsletter", "subscribe", "email list"]),
            "copyright_year": self._extract_copyright_year(text),
        }

    def _extract_copyright_year(self, text: str) -> Optional[str]:
        match = re.search(r"©\s*(\d{4})", text)
        return match.group(1) if match else None

    def _trust_signals(self, soup: BeautifulSoup, pages: dict) -> dict:
        all_text = soup.get_text().lower()
        for page_data in pages.values():
            all_text += " " + page_data.get("text_preview", "").lower()

        social_links = self._detect_social_links(soup)

        return {
            "social_links_found": social_links,
            "social_link_count": len(social_links),
            "has_team_page": "our team" in all_text or "meet the team" in all_text or "about us" in all_text,
            "has_physical_address": self._has_address(all_text),
            "has_phone_number": bool(self._extract_phones(all_text)),
            "has_certifications": any(w in all_text for w in ["certified", "certification", "licensed", "accredited"]),
            "has_client_logos": bool(soup.find_all(class_=re.compile(r"client|partner|logo|brand", re.I))),
            "has_case_studies": "case stud" in all_text or "success stor" in all_text,
            "has_privacy_policy": "privacy policy" in all_text or "privacy" in all_text,
            "has_terms": "terms of service" in all_text or "terms and conditions" in all_text,
            "has_google_reviews_widget": "google" in str(soup).lower() and "review" in str(soup).lower(),
            "has_bbb": "better business bureau" in all_text or "bbb" in all_text,
            "has_years_in_business": self._years_in_business(all_text),
        }

    def _detect_social_links(self, soup: BeautifulSoup) -> list:
        platforms = {
            "facebook": "facebook.com",
            "instagram": "instagram.com",
            "twitter": "twitter.com",
            "linkedin": "linkedin.com",
            "youtube": "youtube.com",
            "tiktok": "tiktok.com",
            "pinterest": "pinterest.com",
        }
        found = []
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            for platform, domain in platforms.items():
                if domain in href:
                    found.append({"platform": platform, "url": link["href"]})
                    break
        return found

    def _has_address(self, text: str) -> bool:
        patterns = [r"\d+\s+\w+\s+(st|ave|blvd|rd|dr|ln|way|ct)\b", r"\b\d{5}\b", "address", "located at"]
        return any(re.search(p, text, re.I) for p in patterns)

    def _years_in_business(self, text: str) -> Optional[str]:
        patterns = [
            r"(\d+)\s*\+?\s*years?\s*(of\s*)?(experience|business|serving|in\s*business)",
            r"since\s+(\d{4})",
            r"established\s+(\d{4})",
            r"founded\s+(\d{4})",
        ]
        for p in patterns:
            match = re.search(p, text, re.I)
            if match:
                return match.group(0)
        return None

    def _conversion_signals(self, soup: BeautifulSoup, pages: dict) -> dict:
        all_text = soup.get_text().lower()
        cta_data = self._detect_ctas(soup)

        hero = soup.find(class_=re.compile(r"hero|banner|jumbotron", re.I))
        hero_has_value_prop = False
        if hero:
            hero_text = hero.get_text().lower()
            hero_has_value_prop = len(hero_text.split()) > 15

        return {
            "total_ctas_homepage": cta_data["count"],
            "above_fold_cta": cta_data["above_fold_cta"],
            "cta_examples": cta_data["examples"],
            "has_free_offer": any(w in all_text for w in ["free consultation", "free quote", "free trial", "free audit", "no cost"]),
            "has_urgency": any(w in all_text for w in ["limited time", "today only", "hurry", "expires", "deadline", "act now"]),
            "has_social_proof_numbers": bool(re.search(r"\d+\s*(clients?|customers?|projects?|years?|businesses?)", all_text)),
            "hero_has_value_prop": hero_has_value_prop,
            "booking_system": any(w in str(soup).lower() for w in ["calendly", "acuity", "booking", "schedule", "appointlet"]),
            "has_money_back_guarantee": "money back" in all_text or "refund" in all_text,
            "pricing_page_exists": "pricing" in pages,
            "contact_page_exists": "contact" in pages,
            "contact_form_exists": bool(soup.find("form")),
            "has_chat_widget": any(w in str(soup).lower() for w in ["intercom", "drift", "crisp", "tawk", "hubspot", "tidio"]),
        }

    def _content_signals(self, soup: BeautifulSoup, pages: dict) -> dict:
        all_text = soup.get_text(separator=" ", strip=True)
        word_count = len(all_text.split())

        last_updated = None
        for meta in soup.find_all("meta"):
            if meta.get("name") in ["last-modified", "revised", "date"]:
                last_updated = meta.get("content")

        return {
            "homepage_word_count": len(soup.get_text().split()),
            "total_pages_scraped": len(pages) + 1,
            "has_blog": "blog" in pages,
            "blog_post_count_estimate": self._estimate_blog_posts(pages),
            "content_freshness_signals": last_updated,
            "has_location_specific_content": self._has_location_content(all_text),
            "service_pages_count": len([p for p in pages if "service" in p.lower()]),
            "has_how_it_works": any(w in all_text.lower() for w in ["how it works", "how we work", "our process", "step by step"]),
            "value_proposition_clarity": self._assess_value_prop(soup),
            "readability_estimate": self._estimate_readability(all_text),
        }

    def _estimate_blog_posts(self, pages: dict) -> Optional[int]:
        if "blog" not in pages:
            return 0
        blog_data = pages["blog"]
        article_count = len(blog_data.get("h2_tags", []))
        return article_count if article_count > 0 else None

    def _has_location_content(self, text: str) -> bool:
        location_words = ["serving", "located", "near", "in the area", "local", "city", "county", "state"]
        return any(w in text.lower() for w in location_words)

    def _assess_value_prop(self, soup: BeautifulSoup) -> dict:
        hero = soup.find(class_=re.compile(r"hero|banner|jumbotron|above", re.I))
        if not hero:
            hero = soup.find("header")
        if not hero:
            return {"has_clear_value_prop": False, "headline": None}

        h1 = hero.find("h1")
        p_tag = hero.find("p")
        headline = h1.get_text(strip=True) if h1 else None
        subheadline = p_tag.get_text(strip=True) if p_tag else None

        vague_words = ["welcome", "best", "great", "amazing", "leading", "top", "excellent"]
        is_vague = headline and any(w in headline.lower() for w in vague_words)

        return {
            "has_clear_value_prop": bool(headline),
            "headline": headline,
            "subheadline": subheadline,
            "headline_is_vague": is_vague,
        }

    def _estimate_readability(self, text: str) -> str:
        sentences = re.split(r"[.!?]+", text)
        words = text.split()
        if not sentences or not words:
            return "unknown"
        avg_sentence_length = len(words) / max(len(sentences), 1)
        if avg_sentence_length < 15:
            return "easy"
        elif avg_sentence_length < 25:
            return "moderate"
        else:
            return "complex"

    def _technical_signals(self, soup: BeautifulSoup) -> dict:
        html = str(soup)

        analytics = {
            "google_analytics": "google-analytics.com" in html or "gtag" in html or "ga(" in html,
            "google_tag_manager": "googletagmanager" in html,
            "facebook_pixel": "fbq(" in html or "facebook.net/en_US/fbevents" in html,
            "hotjar": "hotjar" in html,
            "hubspot": "hubspot" in html,
            "mailchimp": "mailchimp" in html,
        }

        return {
            "analytics_installed": analytics,
            "has_google_analytics": analytics["google_analytics"],
            "has_facebook_pixel": analytics["facebook_pixel"],
            "has_tag_manager": analytics["google_tag_manager"],
            "has_retargeting_pixel": analytics["facebook_pixel"],
            "cms_detected": self._detect_cms(html),
            "has_ssl": self.base_url.startswith("https"),
            "meta_viewport": bool(soup.find("meta", {"name": "viewport"})),
            "canonical_tag": bool(soup.find("link", {"rel": "canonical"})),
            "robots_meta": soup.find("meta", {"name": "robots"}) and
                           soup.find("meta", {"name": "robots"}).get("content", ""),
        }

    def _detect_cms(self, html: str) -> Optional[str]:
        cms_patterns = {
            "WordPress": "wp-content",
            "Shopify": "shopify",
            "Squarespace": "squarespace",
            "Wix": "wix.com",
            "Webflow": "webflow",
            "HubSpot": "hubspot",
            "Drupal": "drupal",
            "Joomla": "joomla",
            "Framer": "framer",
        }
        for cms, pattern in cms_patterns.items():
            if pattern in html.lower():
                return cms
        return "custom/unknown"

    def _navigation_signals(self, soup: BeautifulSoup) -> dict:
        nav = soup.find("nav") or soup.find(class_=re.compile(r"nav|menu", re.I))
        if not nav:
            return {"has_navigation": False}

        nav_links = nav.find_all("a")
        return {
            "has_navigation": True,
            "nav_link_count": len(nav_links),
            "nav_labels": [a.get_text(strip=True) for a in nav_links if a.get_text(strip=True)][:15],
            "has_dropdown": bool(nav.find(class_=re.compile(r"dropdown|submenu", re.I))),
            "has_search": bool(nav.find(["input", "form"])),
        }
