"""
Deep Content Analyzer — goes far beyond word count.
Analyzes copy quality, emotional triggers, clarity, persuasion elements,
and what's missing vs what high-converting businesses use.
"""
import re
from typing import Optional


POWER_WORDS = {
    "urgency": ["now", "today", "immediately", "urgent", "limited", "expires", "deadline", "hurry", "fast"],
    "trust": ["guaranteed", "proven", "certified", "trusted", "secure", "safe", "verified", "accredited"],
    "value": ["free", "save", "discount", "bonus", "exclusive", "special", "premium", "best"],
    "emotion": ["transform", "imagine", "discover", "finally", "amazing", "incredible", "powerful", "effortless"],
    "social_proof": ["join", "thousands", "clients", "customers", "reviews", "rated", "voted", "award"],
    "pain": ["problem", "struggle", "frustrated", "tired", "worried", "stress", "difficult", "expensive"],
    "outcome": ["results", "success", "achieve", "grow", "increase", "improve", "boost", "maximize"],
}

WEAK_PHRASES = [
    "welcome to", "we are proud", "we strive to", "we are committed",
    "leading provider", "best in class", "world class", "cutting edge",
    "state of the art", "one stop shop", "synergy", "leverage",
    "passion for", "dedicated team", "years of experience",
]

CONVERSION_ELEMENTS = {
    "specificity": {
        "patterns": [r"\d+%", r"\d+\s*(clients?|customers?|businesses?|projects?)", r"\$\d+"],
        "description": "Specific numbers (%, $, client counts)",
    },
    "risk_reversal": {
        "patterns": [r"guarantee", r"money.back", r"no.risk", r"free.trial", r"cancel.anytime"],
        "description": "Risk reversal (guarantee, money-back)",
    },
    "social_proof": {
        "patterns": [r"testimonial", r"review", r"client said", r"customer said", r"case stud"],
        "description": "Social proof elements",
    },
    "clear_process": {
        "patterns": [r"how it works", r"step \d", r"our process", r"3 steps", r"simple steps"],
        "description": "Clear process/how it works",
    },
    "pain_points": {
        "patterns": [r"frustrated", r"tired of", r"struggling", r"the problem", r"stop losing"],
        "description": "Addresses customer pain points",
    },
    "outcome_focus": {
        "patterns": [r"you (will|can|get|achieve)", r"your business", r"your (results|growth|revenue)"],
        "description": "Outcome-focused copy (you, your results)",
    },
    "urgency": {
        "patterns": [r"limited", r"today", r"this week", r"expires", r"only \d+"],
        "description": "Urgency/scarcity elements",
    },
    "authority": {
        "patterns": [r"award", r"featured in", r"as seen on", r"certified", r"\d+ years"],
        "description": "Authority/credibility signals",
    },
}


class ContentDeepAuditor:
    def __init__(self, website_data: dict):
        self.website_data = website_data

    def audit(self) -> dict:
        homepage = self.website_data.get("homepage", {})
        pages = self.website_data.get("internal_pages", {})

        all_text = self._collect_all_text(homepage, pages)
        homepage_text = homepage.get("text_preview", "") or ""

        return {
            "copy_quality": self._analyze_copy_quality(all_text, homepage_text),
            "power_words": self._analyze_power_words(all_text),
            "weak_phrases": self._find_weak_phrases(all_text),
            "conversion_elements": self._check_conversion_elements(all_text),
            "value_proposition": self._analyze_value_proposition(homepage),
            "cta_quality": self._analyze_cta_quality(homepage),
            "content_strategy": self._assess_content_strategy(homepage, pages),
            "content_score": self._calculate_content_score(all_text, homepage),
            "missing_elements": self._identify_missing_elements(all_text),
        }

    def _collect_all_text(self, homepage: dict, pages: dict) -> str:
        texts = [homepage.get("text_preview", "") or ""]
        for page_data in pages.values():
            texts.append(page_data.get("text_preview", "") or "")
        return " ".join(texts).lower()

    def _analyze_copy_quality(self, all_text: str, homepage_text: str) -> dict:
        words = all_text.split()
        sentences = re.split(r"[.!?]+", all_text)
        avg_sentence_len = len(words) / max(len(sentences), 1)

        you_count = len(re.findall(r"\byou\b|\byour\b", all_text))
        we_count = len(re.findall(r"\bwe\b|\bour\b|\bus\b", all_text))

        customer_focus_ratio = you_count / max(we_count, 1)

        passive_voice = len(re.findall(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", all_text))

        return {
            "avg_sentence_length": round(avg_sentence_len, 1),
            "readability": "Easy" if avg_sentence_len < 15 else "Moderate" if avg_sentence_len < 25 else "Complex",
            "you_vs_we_ratio": round(customer_focus_ratio, 2),
            "customer_focused": customer_focus_ratio > 1.0,
            "you_count": you_count,
            "we_count": we_count,
            "passive_voice_instances": passive_voice,
            "copy_is_self_focused": we_count > you_count * 1.5,
            "issue": "Copy is too self-focused (too many 'we/our' vs 'you/your') — customers care about their results, not your story" if we_count > you_count * 1.5 else None,
        }

    def _analyze_power_words(self, text: str) -> dict:
        found_by_category = {}
        total_found = 0

        for category, words in POWER_WORDS.items():
            found = [w for w in words if w in text]
            found_by_category[category] = found
            total_found += len(found)

        missing_categories = [cat for cat, found in found_by_category.items() if not found]

        return {
            "total_power_words": total_found,
            "by_category": found_by_category,
            "missing_categories": missing_categories,
            "power_word_density": "High" if total_found > 15 else "Medium" if total_found > 7 else "Low",
            "missing_urgency_words": not bool(found_by_category.get("urgency")),
            "missing_pain_acknowledgment": not bool(found_by_category.get("pain")),
            "issue": f"Copy lacks urgency and pain-point language — categories missing: {', '.join(missing_categories)}" if len(missing_categories) > 3 else None,
        }

    def _find_weak_phrases(self, text: str) -> dict:
        found = [phrase for phrase in WEAK_PHRASES if phrase in text]
        return {
            "weak_phrases_found": found,
            "count": len(found),
            "issue": f"Cliché phrases found: '{found[0]}' — these are ignored by readers and damage credibility" if found else None,
        }

    def _check_conversion_elements(self, text: str) -> dict:
        results = {}
        missing = []
        present = []

        for element, config in CONVERSION_ELEMENTS.items():
            found = any(re.search(p, text, re.I) for p in config["patterns"])
            results[element] = {
                "present": found,
                "description": config["description"],
            }
            if found:
                present.append(element)
            else:
                missing.append(element)

        score = len(present) / len(CONVERSION_ELEMENTS) * 100

        return {
            "elements_present": present,
            "elements_missing": missing,
            "conversion_readiness_score": round(score),
            "critical_missing": [e for e in missing if e in ["risk_reversal", "social_proof", "clear_process"]],
            "issue": f"Missing {len(missing)} key conversion elements: {', '.join(missing[:3])}" if len(missing) > 3 else None,
        }

    def _analyze_value_proposition(self, homepage: dict) -> dict:
        vp = self.website_data.get("content_signals", {}).get("value_proposition_clarity", {})
        headline = vp.get("headline", "")
        subheadline = vp.get("subheadline", "")

        if not headline:
            return {
                "has_value_prop": False,
                "clarity": "None",
                "issue": "No clear headline/value proposition on homepage — visitors don't know what you do in 5 seconds",
            }

        words = headline.split()
        is_specific = bool(re.search(r"\d+|%|\$", headline))
        is_outcome = any(w in headline.lower() for w in ["get", "grow", "save", "increase", "reduce", "stop", "start"])
        is_audience = any(w in headline.lower() for w in ["for", "business", "owners", "homeowners", "companies"])
        is_vague = vp.get("headline_is_vague", False)

        clarity_score = sum([is_specific, is_outcome, is_audience, not is_vague, len(words) > 5])

        return {
            "has_value_prop": True,
            "headline": headline,
            "subheadline": subheadline,
            "is_specific": is_specific,
            "is_outcome_focused": is_outcome,
            "mentions_audience": is_audience,
            "is_vague": is_vague,
            "clarity_score": clarity_score,
            "clarity": "Strong" if clarity_score >= 4 else "Moderate" if clarity_score >= 2 else "Weak",
            "issue": f"Headline '{headline[:50]}...' is vague — doesn't tell visitors what you do or the outcome they get" if is_vague and clarity_score < 2 else None,
        }

    def _analyze_cta_quality(self, homepage: dict) -> dict:
        ctas = homepage.get("has_cta_buttons", {})
        examples = ctas.get("examples", [])

        weak_ctas = ["click here", "learn more", "read more", "submit", "go", "ok", "next"]
        strong_ctas = ["get", "start", "book", "schedule", "claim", "download", "try", "join", "discover"]

        weak_found = [c for c in examples if any(w in c.lower() for w in weak_ctas)]
        strong_found = [c for c in examples if any(w in c.lower() for w in strong_ctas)]

        return {
            "total_ctas": ctas.get("count", 0),
            "above_fold_cta": ctas.get("above_fold_cta", False),
            "cta_examples": examples,
            "weak_ctas_found": weak_found,
            "strong_ctas_found": strong_found,
            "has_value_in_cta": bool(strong_found),
            "no_above_fold_cta": not ctas.get("above_fold_cta", False),
            "issue": "Weak CTA language ('Learn More', 'Click Here') — action-specific CTAs convert 202% more (HubSpot)" if weak_found and not strong_found else
                     "No CTA above the fold — 47% more clicks for above-fold CTAs" if not ctas.get("above_fold_cta", False) else None,
        }

    def _assess_content_strategy(self, homepage: dict, pages: dict) -> dict:
        has_blog = "blog" in pages
        has_case_studies = self.website_data.get("trust_signals", {}).get("has_case_studies", False)
        has_faq = homepage.get("has_faq", False)
        has_how_it_works = self.website_data.get("content_signals", {}).get("has_how_it_works", False)

        strategy_score = sum([has_blog, has_case_studies, has_faq, has_how_it_works])

        return {
            "has_blog": has_blog,
            "has_case_studies": has_case_studies,
            "has_faq": has_faq,
            "has_how_it_works": has_how_it_works,
            "content_strategy_score": strategy_score,
            "grade": "Strong" if strategy_score >= 3 else "Moderate" if strategy_score >= 2 else "Weak",
            "missing": [k for k, v in {
                "blog": has_blog,
                "case studies": has_case_studies,
                "FAQ section": has_faq,
                "how it works": has_how_it_works,
            }.items() if not v],
        }

    def _calculate_content_score(self, all_text: str, homepage: dict) -> dict:
        checks = {
            "has_power_words": len([w for cat in POWER_WORDS.values() for w in cat if w in all_text]) > 5,
            "no_weak_phrases": sum(1 for p in WEAK_PHRASES if p in all_text) == 0,
            "customer_focused": len(re.findall(r"\byou\b|\byour\b", all_text)) > len(re.findall(r"\bwe\b|\bour\b", all_text)),
            "has_specifics": bool(re.search(r"\d+%|\$\d+|\d+\s+clients", all_text)),
            "has_cta": homepage.get("has_cta_buttons", {}).get("count", 0) > 0,
            "above_fold_cta": homepage.get("has_cta_buttons", {}).get("above_fold_cta", False),
            "addresses_pain": any(w in all_text for w in POWER_WORDS["pain"]),
            "shows_outcomes": any(w in all_text for w in POWER_WORDS["outcome"]),
        }

        score = round(sum(checks.values()) / len(checks) * 100)
        return {
            "score": score,
            "grade": "Strong" if score >= 75 else "Moderate" if score >= 50 else "Weak",
            "checks": checks,
        }

    def _identify_missing_elements(self, all_text: str) -> list:
        missing = []

        if not re.search(r"\d+%|\d+\s+(clients?|customers?|businesses?)", all_text):
            missing.append({
                "element": "Social proof numbers",
                "example": "'We've helped 200+ businesses' or 'Clients see 43% average growth'",
                "impact": "Specific numbers increase trust and credibility by 2.4x",
            })

        if not re.search(r"guarantee|money.back|no.risk|free.trial", all_text, re.I):
            missing.append({
                "element": "Risk reversal / guarantee",
                "example": "'30-day money back guarantee' or 'No results, no fee'",
                "impact": "Guarantees increase conversion by up to 35% by removing purchase anxiety",
            })

        if not re.search(r"how it works|step \d|our process", all_text, re.I):
            missing.append({
                "element": "Clear process explanation",
                "example": "3-step 'how it works' section",
                "impact": "Process clarity reduces anxiety and increases qualified inquiries",
            })

        if not re.search(r"faq|frequently asked|common questions", all_text, re.I):
            missing.append({
                "element": "FAQ section",
                "example": "Answer top 5-7 objections before they're asked",
                "impact": "FAQs reduce friction, capture long-tail SEO, and handle objections at scale",
            })

        if not re.search(r"case stud|success stor|before.and.after|results", all_text, re.I):
            missing.append({
                "element": "Case studies / results",
                "example": "'Before: 12 leads/month → After: 67 leads/month'",
                "impact": "Case studies are the #1 most influential content type for B2B decisions (CMI)",
            })

        return missing
