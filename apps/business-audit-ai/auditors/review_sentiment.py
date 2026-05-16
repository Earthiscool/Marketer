"""
Review Sentiment Analyzer — scrapes actual review text and finds recurring
themes, complaints, and praise patterns the business owner likely doesn't know.
"""
import requests
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Optional
from collections import Counter


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

NEGATIVE_SIGNALS = [
    "wait", "slow", "rude", "expensive", "overpriced", "never", "disappointed",
    "terrible", "horrible", "worst", "bad", "poor", "awful", "dirty", "broken",
    "ignored", "unprofessional", "unresponsive", "problem", "issue", "mistake",
    "wrong", "late", "never again", "avoid", "waste", "scam", "lied",
]

POSITIVE_SIGNALS = [
    "great", "excellent", "amazing", "love", "best", "fantastic", "wonderful",
    "recommend", "helpful", "friendly", "professional", "knowledgeable", "fast",
    "quality", "clean", "easy", "perfect", "exceptional", "outstanding",
    "impressive", "thorough", "efficient", "responsive", "reliable",
]

THEME_KEYWORDS = {
    "customer_service": ["staff", "service", "employee", "rep", "team", "helpful", "rude", "friendly", "attitude"],
    "pricing": ["price", "expensive", "cheap", "cost", "worth", "overpriced", "value", "affordable"],
    "quality": ["quality", "product", "material", "durable", "broke", "works", "excellent quality"],
    "speed": ["fast", "slow", "quick", "wait", "long", "delay", "immediately", "same day"],
    "communication": ["called", "email", "respond", "back", "contacted", "reply", "communication"],
    "location_parking": ["parking", "location", "far", "convenient", "nearby", "distance"],
    "knowledge": ["knowledgeable", "expert", "advice", "recommend", "guided", "helped"],
    "cleanliness": ["clean", "dirty", "organized", "messy", "neat", "tidy"],
}


class ReviewSentimentAuditor:
    def __init__(self, business_name: Optional[str], url: str):
        self.business_name = business_name
        self.url = url

    def audit(self) -> dict:
        if not self.business_name:
            return {"skipped": True, "reason": "No business name provided"}

        reviews = self._scrape_review_snippets()
        if not reviews:
            return {"reviews_found": 0, "sentiment": None}

        sentiment = self._analyze_sentiment(reviews)
        themes = self._extract_themes(reviews)
        patterns = self._find_patterns(reviews)

        return {
            "reviews_analyzed": len(reviews),
            "sentiment_breakdown": sentiment,
            "top_themes": themes,
            "recurring_patterns": patterns,
            "insights": self._generate_insights(sentiment, themes, patterns),
        }

    def _scrape_review_snippets(self) -> list:
        reviews = []

        # Try Google search for review snippets
        reviews.extend(self._google_review_snippets())

        # Try Yelp
        yelp_reviews = self._yelp_review_snippets()
        reviews.extend(yelp_reviews)

        return reviews[:30]

    def _google_review_snippets(self) -> list:
        try:
            query = f'{self.business_name} reviews'
            r = requests.get(
                f"https://www.google.com/search?q={quote_plus(query)}",
                headers=HEADERS, timeout=10
            )
            soup = BeautifulSoup(r.text, "lxml")
            text = r.text

            reviews = []

            # Extract review snippets from search results
            # Google shows review snippets in various formats
            snippet_patterns = [
                r'"([^"]{30,200})"',  # quoted text
            ]

            # Look for star rating + review text patterns
            review_sections = soup.find_all(class_=re.compile(r"review|rating|testimonial", re.I))
            for section in review_sections:
                text_content = section.get_text(strip=True)
                if len(text_content) > 20:
                    reviews.append({"text": text_content[:300], "source": "google"})

            # Also extract from structured data
            scripts = soup.find_all("script", {"type": "application/ld+json"})
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "Review":
                        body = data.get("reviewBody", "")
                        if body:
                            reviews.append({"text": body[:300], "source": "schema"})
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == "Review":
                                body = item.get("reviewBody", "")
                                if body:
                                    reviews.append({"text": body[:300], "source": "schema"})
                except Exception:
                    pass

            return reviews[:15]
        except Exception:
            return []

    def _yelp_review_snippets(self) -> list:
        try:
            query = self.business_name
            r = requests.get(
                f"https://www.yelp.com/search?find_desc={quote_plus(query)}",
                headers=HEADERS, timeout=10
            )
            soup = BeautifulSoup(r.text, "lxml")

            reviews = []
            # Yelp review snippets in search results
            snippets = soup.find_all(class_=re.compile(r"reviewText|review-content|snippet", re.I))
            for s in snippets[:10]:
                text = s.get_text(strip=True)
                if len(text) > 20:
                    reviews.append({"text": text[:300], "source": "yelp"})

            # Also check structured data
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        for review in data.get("reviews", []):
                            body = review.get("reviewBody", "")
                            if body:
                                reviews.append({"text": body[:300], "source": "yelp_schema"})
                except Exception:
                    pass

            return reviews[:10]
        except Exception:
            return []

    def _analyze_sentiment(self, reviews: list) -> dict:
        all_text = " ".join(r["text"].lower() for r in reviews)
        words = all_text.split()

        positive_count = sum(1 for w in words if w in POSITIVE_SIGNALS)
        negative_count = sum(1 for w in words if w in NEGATIVE_SIGNALS)
        total = positive_count + negative_count

        if total == 0:
            sentiment_ratio = 0.5
        else:
            sentiment_ratio = positive_count / total

        # Find specific negative phrases
        negative_phrases = []
        for review in reviews:
            text = review["text"].lower()
            for signal in NEGATIVE_SIGNALS:
                if signal in text:
                    # Extract surrounding context
                    idx = text.find(signal)
                    context = text[max(0, idx-30):idx+50]
                    negative_phrases.append(context.strip())

        # Find specific positive phrases
        positive_phrases = []
        for review in reviews:
            text = review["text"].lower()
            for signal in POSITIVE_SIGNALS[:5]:
                if signal in text:
                    idx = text.find(signal)
                    context = text[max(0, idx-20):idx+60]
                    positive_phrases.append(context.strip())

        return {
            "positive_mentions": positive_count,
            "negative_mentions": negative_count,
            "sentiment_score": round(sentiment_ratio * 100),
            "overall": "Positive" if sentiment_ratio > 0.7 else "Mixed" if sentiment_ratio > 0.4 else "Negative",
            "top_negative_phrases": list(set(negative_phrases))[:5],
            "top_positive_phrases": list(set(positive_phrases))[:5],
        }

    def _extract_themes(self, reviews: list) -> dict:
        all_text = " ".join(r["text"].lower() for r in reviews)
        theme_scores = {}

        for theme, keywords in THEME_KEYWORDS.items():
            score = sum(all_text.count(kw) for kw in keywords)
            if score > 0:
                theme_scores[theme] = score

        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)

        return {
            "top_themes": [{"theme": t, "mentions": c} for t, c in sorted_themes[:5]],
            "theme_scores": theme_scores,
        }

    def _find_patterns(self, reviews: list) -> list:
        all_text = " ".join(r["text"].lower() for r in reviews)
        patterns = []

        # Find repeated specific words (2+ syllables, meaningful)
        words = re.findall(r'\b[a-z]{5,}\b', all_text)
        word_counts = Counter(words)
        stop_words = {"their", "there", "these", "about", "would", "could", "should",
                      "really", "great", "place", "store", "staff", "always", "never",
                      "every", "other", "where", "which", "while", "after", "before",
                      "people", "think", "going", "years", "times", "still", "first"}

        recurring = [(w, c) for w, c in word_counts.most_common(30)
                     if w not in stop_words and c >= 2]

        for word, count in recurring[:8]:
            # Determine if positive or negative context
            contexts = []
            for review in reviews:
                text = review["text"].lower()
                if word in text:
                    idx = text.find(word)
                    contexts.append(text[max(0, idx-40):idx+60])

            patterns.append({
                "word": word,
                "mentions": count,
                "sample_context": contexts[0] if contexts else "",
            })

        return patterns

    def _generate_insights(self, sentiment: dict, themes: dict, patterns: list) -> list:
        insights = []

        if sentiment.get("overall") == "Negative":
            insights.append({
                "type": "reputation_risk",
                "finding": f"Review sentiment analysis shows {sentiment.get('negative_mentions', 0)} negative signals vs {sentiment.get('positive_mentions', 0)} positive",
                "impact": "Negative review patterns actively driving customers to competitors",
            })

        top_themes = themes.get("top_themes", [])
        if top_themes:
            top = top_themes[0]
            theme_name = top["theme"].replace("_", " ")
            insights.append({
                "type": "recurring_theme",
                "finding": f"'{theme_name}' is the most mentioned theme across reviews ({top['mentions']} mentions)",
                "impact": f"This is what customers associate most with the business — good or bad",
            })

        neg_phrases = sentiment.get("top_negative_phrases", [])
        if neg_phrases:
            insights.append({
                "type": "complaint_pattern",
                "finding": f"Recurring complaint language detected: '{neg_phrases[0]}'",
                "impact": "Systematic issue that keeps surfacing — not random one-off complaints",
            })

        return insights
