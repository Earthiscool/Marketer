"""
SEO Auditor — deeply analyzes on-page SEO signals.
Checks meta tags, structure, keyword signals, local SEO, schema, and more.
"""
import re
from urllib.parse import urlparse
from typing import Optional


class SEOAuditor:
    def __init__(self, url: str, website_data: dict):
        self.url = url
        self.domain = urlparse(url).netloc
        self.website_data = website_data

    def audit(self) -> dict:
        homepage = self.website_data.get("homepage", {})
        pages = self.website_data.get("internal_pages", {})
        tech = self.website_data.get("technical_signals", {})
        nav = self.website_data.get("navigation", {})

        return {
            "title_analysis": self._analyze_title(homepage),
            "meta_description": self._check_meta_description(homepage),
            "heading_structure": self._analyze_headings(homepage, pages),
            "keyword_signals": self._keyword_signals(homepage, pages),
            "content_depth": self._content_depth(homepage, pages),
            "local_seo": self._local_seo_signals(homepage, pages),
            "schema_analysis": homepage.get("schema_markup", {}),
            "image_seo": self._image_seo(homepage, pages),
            "internal_linking": self._internal_linking(homepage, pages),
            "technical_seo": self._technical_seo(tech, homepage),
            "page_coverage": self._page_coverage(pages),
            "seo_score": self._calculate_seo_score(homepage, pages, tech),
        }

    def _analyze_title(self, homepage: dict) -> dict:
        title = homepage.get("title")
        if not title:
            return {
                "exists": False,
                "length": 0,
                "optimal_length": False,
                "issue": "Missing title tag — critical SEO issue"
            }

        length = len(title)
        return {
            "exists": True,
            "value": title,
            "length": length,
            "optimal_length": 50 <= length <= 60,
            "too_short": length < 30,
            "too_long": length > 70,
            "issue": "Title too long, gets cut off in search results" if length > 70 else
                     "Title too short, missing keyword opportunity" if length < 30 else None,
        }

    def _check_meta_description(self, homepage: dict) -> dict:
        desc = homepage.get("meta_description")
        if not desc:
            return {
                "exists": False,
                "length": 0,
                "optimal_length": False,
                "issue": "Missing meta description — Google writes its own, often poorly",
            }
        length = len(desc)
        return {
            "exists": True,
            "value": desc,
            "length": length,
            "optimal_length": 120 <= length <= 160,
            "too_short": length < 70,
            "too_long": length > 160,
            "issue": "Meta description too long — gets truncated in search results" if length > 160 else
                     "Meta description too short — missing keyword and click opportunity" if length < 70 else None,
        }

    def _analyze_headings(self, homepage: dict, pages: dict) -> dict:
        h1s = homepage.get("h1_tags", [])
        h2s = homepage.get("h2_tags", [])

        all_page_issues = []
        for page_name, page_data in pages.items():
            page_h1s = page_data.get("h1_tags", [])
            if len(page_h1s) == 0:
                all_page_issues.append(f"{page_name}: missing H1")
            elif len(page_h1s) > 1:
                all_page_issues.append(f"{page_name}: multiple H1s ({len(page_h1s)})")

        return {
            "homepage_h1_count": len(h1s),
            "homepage_h1_text": h1s,
            "homepage_h2_count": len(h2s),
            "homepage_h2_examples": h2s[:5],
            "missing_h1": len(h1s) == 0,
            "multiple_h1s": len(h1s) > 1,
            "good_h2_structure": len(h2s) >= 3,
            "page_issues": all_page_issues,
            "issue": "No H1 tag on homepage — major SEO signal missing" if len(h1s) == 0 else
                     "Multiple H1s on homepage — confuses search engines" if len(h1s) > 1 else None,
        }

    def _keyword_signals(self, homepage: dict, pages: dict) -> dict:
        all_headings = homepage.get("h1_tags", []) + homepage.get("h2_tags", []) + homepage.get("h3_tags", [])
        all_heading_text = " ".join(all_headings).lower()

        service_page = pages.get("services", {})
        service_headings = service_page.get("h1_tags", []) + service_page.get("h2_tags", []) if service_page else []

        location_keywords = re.findall(
            r'\b(in|near|serving|located in|[A-Z][a-z]+ (city|county|area|region))\b',
            homepage.get("text_preview", ""),
        )

        return {
            "service_mentioned_in_headings": len(service_headings) > 0,
            "location_mentioned_in_headings": bool(location_keywords),
            "heading_keyword_count": len(all_headings),
            "value_proposition_in_h1": len(homepage.get("h1_tags", [])) > 0 and
                                        len(homepage["h1_tags"][0].split()) > 3,
            "headings_sample": all_headings[:8],
            "no_service_page": "services" not in pages,
            "issue": "No service/product-specific keywords found in headings" if len(all_headings) < 3 else None,
        }

    def _content_depth(self, homepage: dict, pages: dict) -> dict:
        homepage_words = homepage.get("word_count", 0)
        page_word_counts = {name: data.get("word_count", 0) for name, data in pages.items()}
        total_words = homepage_words + sum(page_word_counts.values())

        thin_pages = [name for name, count in page_word_counts.items() if 0 < count < 300]

        return {
            "homepage_word_count": homepage_words,
            "total_indexed_word_count": total_words,
            "page_word_counts": page_word_counts,
            "thin_content_pages": thin_pages,
            "homepage_content_grade": "Good" if homepage_words > 500 else
                                      "Thin" if homepage_words > 200 else "Very Thin",
            "has_blog": "blog" in pages,
            "blog_drives_seo": "blog" in pages and page_word_counts.get("blog", 0) > 500,
            "issue": f"Thin homepage content ({homepage_words} words). Google prefers 500+ for service pages." if homepage_words < 300 else None,
        }

    def _local_seo_signals(self, homepage: dict, pages: dict) -> dict:
        trust = self.website_data.get("trust_signals", {})
        schema = homepage.get("schema_markup", {})
        all_text = homepage.get("text_preview", "").lower()

        for page_data in pages.values():
            all_text += " " + page_data.get("text_preview", "").lower()

        return {
            "has_local_business_schema": schema.get("has_local_business", False),
            "has_address_on_site": trust.get("has_physical_address", False),
            "has_phone_number": trust.get("has_phone_number", False),
            "nap_consistency_possible": trust.get("has_physical_address", False) and trust.get("has_phone_number", False),
            "mentions_city_or_region": bool(re.search(r'\b[A-Z][a-z]+,\s+[A-Z]{2}\b', homepage.get("text_preview", ""))),
            "has_google_maps_embed": "maps.google" in all_text or "google.com/maps" in all_text,
            "missing_local_schema": not schema.get("has_local_business", False),
            "issue": "Missing LocalBusiness schema markup — Google can't properly display your business in local search" if not schema.get("has_local_business", False) else None,
        }

    def _image_seo(self, homepage: dict, pages: dict) -> dict:
        homepage_images = homepage.get("image_count", 0)
        missing_alt = homepage.get("images_missing_alt", 0)

        total_missing = missing_alt
        for page_data in pages.values():
            total_missing += page_data.get("images_missing_alt", 0)

        return {
            "homepage_image_count": homepage_images,
            "homepage_images_missing_alt": missing_alt,
            "total_images_missing_alt": total_missing,
            "alt_tag_ratio": f"{homepage_images - missing_alt}/{homepage_images}" if homepage_images > 0 else "0/0",
            "issue": f"{total_missing} images missing alt text — hurts both SEO and accessibility" if total_missing > 0 else None,
        }

    def _internal_linking(self, homepage: dict, pages: dict) -> dict:
        homepage_links = homepage.get("internal_link_count", 0)
        return {
            "homepage_internal_links": homepage_links,
            "total_pages_found": len(pages) + 1,
            "good_internal_linking": homepage_links >= 5,
            "missing_key_pages": self.website_data.get("global_signals", {}).get("missing_key_pages", []),
        }

    def _technical_seo(self, tech: dict, homepage: dict) -> dict:
        return {
            "has_ssl": tech.get("has_ssl", False),
            "has_viewport_meta": tech.get("meta_viewport", False),
            "has_canonical": tech.get("canonical_tag", False),
            "robots_meta": tech.get("robots_meta"),
            "cms": tech.get("cms_detected"),
            "has_analytics": tech.get("has_google_analytics", False),
            "missing_ssl": not tech.get("has_ssl", False),
            "no_analytics": not tech.get("has_google_analytics", False),
            "issue": "No SSL certificate (HTTP, not HTTPS) — Google penalizes and users see 'Not Secure'" if not tech.get("has_ssl", False) else None,
        }

    def _page_coverage(self, pages: dict) -> dict:
        expected_seo_pages = ["services", "about", "contact", "blog"]
        found = list(pages.keys())
        missing = [p for p in expected_seo_pages if p not in found]
        return {
            "pages_found": found,
            "seo_important_pages_missing": missing,
            "has_dedicated_service_pages": "services" in found,
            "has_blog_for_seo": "blog" in found,
            "no_blog": "blog" not in found,
            "issue": f"Missing key SEO pages: {', '.join(missing)}" if missing else None,
        }

    def _calculate_seo_score(self, homepage: dict, pages: dict, tech: dict) -> dict:
        checks = {
            "has_title": bool(homepage.get("title")),
            "has_h1": len(homepage.get("h1_tags", [])) == 1,
            "has_h2s": len(homepage.get("h2_tags", [])) >= 2,
            "has_ssl": tech.get("has_ssl", False),
            "has_schema": homepage.get("schema_markup", {}).get("has_schema", False),
            "has_blog": "blog" in pages,
            "has_contact": "contact" in pages,
            "has_services": "services" in pages,
            "alt_tags_good": homepage.get("images_missing_alt", 99) == 0,
            "sufficient_content": homepage.get("word_count", 0) > 400,
        }

        passed = sum(checks.values())
        total = len(checks)
        score = round((passed / total) * 100)

        return {
            "score": score,
            "passed": passed,
            "total": total,
            "checks": checks,
            "grade": "Strong" if score >= 80 else "Moderate" if score >= 60 else "Weak",
        }
