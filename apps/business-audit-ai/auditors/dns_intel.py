"""
DNS Intelligence Auditor — digs into DNS records to reveal:
- Email provider (Gmail = personal, Microsoft 365 = professional, custom = enterprise)
- SPF/DKIM/DMARC setup (email marketing sophistication indicator)
- Hosting provider
- Whether they have professional email infrastructure vs owner using @gmail.com
- SSL certificate age from crt.sh (reveals true domain age)
- Subdomains (reveals internal systems: app., crm., shop., etc.)

No API key required — all free, public data.
"""
import socket
import requests
import re
import json
from urllib.parse import urlparse
from typing import Optional


# Email provider detection from MX records
MX_PROVIDERS = {
    "google": ["google.com", "googlemail.com", "gmail.com"],
    "microsoft": ["outlook.com", "hotmail.com", "microsoft.com", "office365.com"],
    "zoho": ["zoho.com", "zohomail.com"],
    "fastmail": ["fastmail.com", "messagingengine.com"],
    "protonmail": ["protonmail.ch", "proton.me"],
    "mailchimp": ["mcsv.net"],
    "sendgrid": ["sendgrid.net"],
    "amazon_ses": ["amazonses.com", "amazonaws.com"],
    "mailgun": ["mailgun.org"],
    "postmark": ["mtasv.net"],
}

# Subdomain signals
INTERESTING_SUBDOMAINS = {
    "app": "Has a web application (SaaS or customer portal)",
    "shop": "Has a separate e-commerce store",
    "crm": "Uses CRM software",
    "portal": "Has a customer portal",
    "dashboard": "Has a dashboard/admin system",
    "api": "Has an API (technically sophisticated)",
    "blog": "Blog is on a subdomain",
    "mail": "Self-hosted email",
    "staging": "Active development (good sign)",
    "dev": "Active development",
    "store": "Separate store subdomain",
    "help": "Has a help center",
    "support": "Has a support system",
    "m": "Has a mobile-specific site (outdated practice)",
}


class DNSIntelAuditor:
    def __init__(self, url: str):
        self.url = url
        parsed = urlparse(url)
        self.domain = parsed.netloc.replace("www.", "")
        self.full_domain = parsed.netloc

    def audit(self) -> dict:
        mx_data = self._get_mx_records()
        txt_data = self._get_txt_records()
        ssl_data = self._get_ssl_intel()
        subdomains = self._discover_subdomains()
        ip_data = self._get_ip_hosting()

        email_infra = self._assess_email_infrastructure(mx_data, txt_data)
        insights = self._generate_insights(mx_data, txt_data, email_infra, subdomains)

        return {
            "domain": self.domain,
            "mx_records": mx_data,
            "email_provider": mx_data.get("provider", "unknown"),
            "email_infrastructure": email_infra,
            "ssl_intel": ssl_data,
            "subdomains_found": subdomains,
            "hosting": ip_data,
            "txt_records_summary": txt_data,
            "insights": insights,
        }

    def _get_mx_records(self) -> dict:
        try:
            import dns.resolver
            answers = dns.resolver.resolve(self.domain, "MX")
            records = sorted([(r.preference, str(r.exchange).lower().rstrip(".")) for r in answers])

            provider = "unknown"
            for pref, host in records:
                for prov, patterns in MX_PROVIDERS.items():
                    if any(p in host for p in patterns):
                        provider = prov
                        break

            return {
                "records": [{"priority": p, "host": h} for p, h in records],
                "provider": provider,
                "has_mx": True,
                "primary_mx": records[0][1] if records else None,
            }
        except ImportError:
            return self._mx_fallback()
        except Exception:
            return {"has_mx": False, "provider": "none", "records": []}

    def _mx_fallback(self) -> dict:
        """Fallback using socket when dnspython not available."""
        try:
            import subprocess
            result = subprocess.run(
                ["host", "-t", "MX", self.domain],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout.lower()
            provider = "unknown"
            for prov, patterns in MX_PROVIDERS.items():
                if any(p in output for p in patterns):
                    provider = prov
                    break
            has_mx = "mail is handled" in output
            return {"has_mx": has_mx, "provider": provider, "records": []}
        except Exception:
            return {"has_mx": False, "provider": "unknown", "records": []}

    def _get_txt_records(self) -> dict:
        has_spf = False
        has_dkim_signal = False
        has_dmarc = False
        spf_value = None

        try:
            import dns.resolver
            try:
                answers = dns.resolver.resolve(self.domain, "TXT")
                for rdata in answers:
                    txt = str(rdata).lower()
                    if "v=spf1" in txt:
                        has_spf = True
                        spf_value = str(rdata)[:100]
                    if "v=dkim" in txt or "dkim" in txt:
                        has_dkim_signal = True
            except Exception:
                pass

            try:
                dmarc_answers = dns.resolver.resolve(f"_dmarc.{self.domain}", "TXT")
                for rdata in dmarc_answers:
                    if "v=dmarc" in str(rdata).lower():
                        has_dmarc = True
            except Exception:
                pass

        except ImportError:
            # Fallback: assume based on provider
            pass

        return {
            "has_spf": has_spf,
            "has_dkim": has_dkim_signal,
            "has_dmarc": has_dmarc,
            "spf_value": spf_value,
            "email_auth_score": sum([has_spf, has_dkim_signal, has_dmarc]),
        }

    def _get_ssl_intel(self) -> dict:
        """Check crt.sh for SSL certificate transparency data."""
        try:
            r = requests.get(
                f"https://crt.sh/?q={self.domain}&output=json",
                timeout=10,
            )
            if r.status_code != 200:
                return {"available": False}

            certs = r.json()
            if not certs:
                return {"available": False, "cert_count": 0}

            # Find earliest cert
            dates = []
            for cert in certs:
                date_str = cert.get("not_before", "")
                if date_str:
                    dates.append(date_str[:10])  # YYYY-MM-DD

            dates.sort()
            earliest = dates[0] if dates else None
            latest = dates[-1] if dates else None

            from datetime import datetime
            domain_age_years = None
            if earliest:
                try:
                    first_cert_date = datetime.strptime(earliest, "%Y-%m-%d")
                    domain_age_years = round((datetime.now() - first_cert_date).days / 365.25, 1)
                except Exception:
                    pass

            # Extract unique subdomains from cert CNs
            cert_subdomains = set()
            for cert in certs[:50]:
                name = cert.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip().lower()
                    if sub.endswith(self.domain) and sub != self.domain and sub != f"*.{self.domain}":
                        sub_prefix = sub.replace(f".{self.domain}", "")
                        if sub_prefix and "*" not in sub_prefix:
                            cert_subdomains.add(sub_prefix)

            return {
                "available": True,
                "cert_count": len(certs),
                "first_cert_date": earliest,
                "latest_cert_date": latest,
                "domain_age_from_ssl_years": domain_age_years,
                "subdomains_in_certs": sorted(list(cert_subdomains))[:20],
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _discover_subdomains(self) -> list:
        """Cross-reference SSL cert subdomains with INTERESTING_SUBDOMAINS."""
        ssl = self._get_ssl_intel()
        found = []
        cert_subs = ssl.get("subdomains_in_certs", [])

        for sub in cert_subs:
            signal = INTERESTING_SUBDOMAINS.get(sub)
            found.append({
                "subdomain": f"{sub}.{self.domain}",
                "prefix": sub,
                "signal": signal or f"Subdomain '{sub}' detected",
            })

        return found[:10]

    def _get_ip_hosting(self) -> dict:
        try:
            ip = socket.gethostbyname(self.domain)
            # Detect provider from IP ranges / rDNS
            try:
                rdns = socket.gethostbyaddr(ip)[0].lower()
            except Exception:
                rdns = ""

            provider = "unknown"
            provider_map = {
                "amazonaws": "AWS", "amazon": "AWS",
                "cloudflare": "Cloudflare",
                "fastly": "Fastly",
                "akamai": "Akamai",
                "googleusercontent": "Google Cloud",
                "azure": "Azure", "microsoft": "Azure",
                "vercel": "Vercel",
                "netlify": "Netlify",
                "wpengine": "WP Engine",
                "kinsta": "Kinsta",
                "godaddy": "GoDaddy",
                "bluehost": "Bluehost",
                "hostgator": "HostGator",
                "siteground": "SiteGround",
                "digitalocean": "DigitalOcean",
                "linode": "Linode",
                "shopify": "Shopify",
                "squarespace": "Squarespace",
                "wix": "Wix",
            }
            for pattern, name in provider_map.items():
                if pattern in rdns:
                    provider = name
                    break

            return {"ip": ip, "rdns": rdns[:60] if rdns else None, "provider": provider}
        except Exception:
            return {"ip": None, "provider": "unknown"}

    def _assess_email_infrastructure(self, mx_data: dict, txt_data: dict) -> dict:
        provider = mx_data.get("provider", "unknown")
        has_mx = mx_data.get("has_mx", False)
        email_auth = txt_data.get("email_auth_score", 0)

        issues = []
        score = 100

        if not has_mx:
            issues.append("No MX records — may not have business email set up at all")
            score -= 40
        elif provider == "google":
            issues.append("Using Google Workspace (Gmail) for business email — professional but common")
        elif provider == "microsoft":
            issues.append("Using Microsoft 365 for email — enterprise-grade setup")
        elif provider == "unknown":
            issues.append("Unknown email provider — may be using personal email address")
            score -= 20

        if not txt_data.get("has_spf"):
            issues.append("No SPF record — cold emails will land in spam; limits email marketing effectiveness")
            score -= 20
        if not txt_data.get("has_dmarc"):
            issues.append("No DMARC record — domain vulnerable to email spoofing/phishing")
            score -= 15
        if not txt_data.get("has_dkim"):
            issues.append("DKIM not detected — reduces email deliverability for marketing campaigns")
            score -= 15

        grade = "enterprise" if score >= 85 else "professional" if score >= 65 else "basic" if score >= 40 else "poor"

        return {
            "score": max(0, score),
            "grade": grade,
            "provider": provider,
            "email_deliverability_ready": email_auth >= 2,
            "issues": issues,
            "cold_email_angle": (
                "Their email infrastructure has no DMARC/SPF — their marketing emails go to spam. "
                "AI email system setup would fix this immediately."
                if email_auth < 2 else None
            ),
        }

    def _generate_insights(self, mx_data, txt_data, email_infra, subdomains) -> list:
        insights = []

        if email_infra.get("score", 100) < 60:
            insights.append({
                "type": "email_infrastructure",
                "finding": f"Email auth score: {email_infra['score']}/100 — missing SPF/DKIM/DMARC",
                "impact": "Any cold outreach or marketing emails likely going to spam",
                "urgency": "high",
            })

        sub_signals = [s for s in subdomains if s.get("signal")]
        if sub_signals:
            insights.append({
                "type": "tech_footprint",
                "finding": f"Subdomains detected: {', '.join(s['prefix'] for s in sub_signals[:4])}",
                "impact": "Reveals internal systems and technology stack",
                "urgency": "medium",
            })

        return insights
