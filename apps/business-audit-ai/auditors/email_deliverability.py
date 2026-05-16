"""
Email Deliverability Auditor — checks SPF, DKIM, DMARC, and MX records via DNS.
A business missing these configs is losing emails to spam AND is trivially spoofable.
Shows up in cold email as a technical credibility hook:
"Your outbound emails are likely hitting spam folders right now."

Uses dnspython (already in requirements.txt). Pure DNS — no API key needed.
"""
from urllib.parse import urlparse
from typing import Optional, Tuple

try:
    import dns.resolver
    import dns.exception
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


# Common DKIM selectors used by major email providers
DKIM_SELECTORS = [
    "google",        # Google Workspace
    "mail",          # Generic
    "default",       # Generic
    "selector1",     # Microsoft 365
    "selector2",     # Microsoft 365 (rotation)
    "k1",            # Klaviyo, Mailchimp
    "dkim",          # Generic
    "s1",            # SendGrid, generic
    "s2",            # Generic
    "email",         # Generic
    "smtp",          # Generic
    "mta",           # Generic
    "mailjet",       # Mailjet
    "sparkpost",     # SparkPost
    "mandrill1",     # Mandrill/Mailchimp
    "cm",            # Campaign Monitor
    "sg",            # SendGrid
    "pm",            # Postmark
]


class EmailDeliverabilityAuditor:
    def __init__(self, url: str):
        parsed = urlparse(url)
        netloc = parsed.netloc or url
        self.domain = netloc.replace("www.", "").split(":")[0]

    def audit(self) -> dict:
        if not DNS_AVAILABLE:
            return {"error": "dnspython not installed", "skipped": True}
        if not self.domain:
            return {"error": "Could not extract domain", "skipped": True}

        has_mx = self._check_mx()
        has_spf, spf_record = self._check_spf()
        dkim_selector, has_dkim = self._check_dkim()
        has_dmarc, dmarc_policy = self._check_dmarc()

        issues = []
        if not has_mx:
            issues.append("No MX records — domain not configured to receive email, may not be active")
        if not has_spf:
            issues.append("No SPF record — outbound emails flagged as spam; domain can be impersonated")
        if not has_dkim:
            issues.append("No DKIM record found — emails lack cryptographic signature, hurts deliverability")
        if not has_dmarc:
            issues.append("No DMARC policy — zero protection against spoofing; anyone can send as this domain")
        elif dmarc_policy == "none":
            issues.append("DMARC policy is 'p=none' — monitoring only, not actually blocking spoofed emails")

        score = 100
        if not has_mx:     score -= 15
        if not has_spf:    score -= 30
        if not has_dkim:   score -= 25
        if not has_dmarc:  score -= 30
        elif dmarc_policy == "none":
            score -= 10

        grade = "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D" if score >= 30 else "F"

        return {
            "domain": self.domain,
            "has_mx":    has_mx,
            "has_spf":   has_spf,
            "spf_record": spf_record,
            "has_dkim":  has_dkim,
            "dkim_selector_found": dkim_selector,
            "has_dmarc": has_dmarc,
            "dmarc_policy": dmarc_policy,
            "deliverability_score": max(0, score),
            "deliverability_grade": grade,
            "issues": issues,
            "issue_count": len(issues),
            "cold_email_angle": self._cold_email_angle(has_spf, has_dkim, has_dmarc, dmarc_policy),
        }

    def _check_mx(self) -> bool:
        try:
            answers = dns.resolver.resolve(self.domain, "MX", lifetime=8)
            return len(list(answers)) > 0
        except Exception:
            return False

    def _check_spf(self) -> Tuple[bool, Optional[str]]:
        try:
            answers = dns.resolver.resolve(self.domain, "TXT", lifetime=8)
            for r in answers:
                txt = r.to_text().strip('"')
                if txt.startswith("v=spf1"):
                    return True, txt[:120]
        except Exception:
            pass
        return False, None

    def _check_dkim(self) -> Tuple[Optional[str], bool]:
        for selector in DKIM_SELECTORS:
            try:
                host = f"{selector}._domainkey.{self.domain}"
                answers = dns.resolver.resolve(host, "TXT", lifetime=5)
                for r in answers:
                    txt = r.to_text()
                    if "v=DKIM1" in txt or "p=" in txt:
                        return selector, True
            except Exception:
                continue
        return None, False

    def _check_dmarc(self) -> Tuple[bool, Optional[str]]:
        try:
            answers = dns.resolver.resolve(f"_dmarc.{self.domain}", "TXT", lifetime=8)
            for r in answers:
                txt = r.to_text()
                if "v=DMARC1" in txt:
                    policy_match = __import__("re").search(r"p=(\w+)", txt)
                    policy = policy_match.group(1) if policy_match else "none"
                    return True, policy
        except Exception:
            pass
        return False, None

    def _cold_email_angle(self, spf: bool, dkim: bool, dmarc: bool, dmarc_policy: Optional[str]) -> Optional[str]:
        missing = []
        if not spf:   missing.append("SPF")
        if not dkim:  missing.append("DKIM")
        if not dmarc: missing.append("DMARC")
        if not missing and dmarc_policy == "none":
            return "Your DMARC policy is set to 'monitor only' — your domain is still fully spoofable and emails may be landing in spam."
        if not missing:
            return None
        return (
            f"Your domain is missing {', '.join(missing)} — your outbound emails are almost certainly "
            f"hitting spam folders, and anyone on the internet can send emails that appear to come from "
            f"@{self.domain}."
        )
