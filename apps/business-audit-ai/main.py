#!/usr/bin/env python3
"""
Business Audit AI
Give it any business URL. It deep-audits their entire online presence —
performance, SEO, reviews, social, conversions — and generates a
personalized cold email with specific, quantified findings.

Usage:
    python main.py <url> [business_name]

Example:
    python main.py https://somelocalbusiness.com "Joe's Plumbing"
"""
import sys
import json
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()
console = Console()


def validate_env():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        console.print("[red]Error: GROQ_API_KEY not set in .env file[/red]")
        console.print("Get a free key at console.groq.com then add it to .env")
        sys.exit(1)
    return key


def normalize_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def run_single_audit(url: str, business_name: str, api_key: str) -> dict:
    from auditors.website import WebsiteAuditor
    from auditors.performance import PerformanceAuditor
    from auditors.seo import SEOAuditor
    from auditors.social import SocialAuditor
    from auditors.reviews import ReviewAuditor
    from auditors.competitors import CompetitorAuditor
    from auditors.ads import AdsAuditor
    from auditors.trends import TrendsAuditor
    from auditors.content_deep import ContentDeepAuditor
    from auditors.funnel import FunnelAuditor
    from auditors.jobs import JobsAuditor
    from auditors.wayback import WaybackAuditor
    from auditors.review_sentiment import ReviewSentimentAuditor
    from auditors.traffic import TrafficAuditor
    from auditors.industry import IndustryAnalyzer
    from auditors.dns_intel import DNSIntelAuditor
    from auditors.tech_stack import TechStackAuditor
    from auditors.visual import VisualAuditor
    from auditors.email_deliverability import EmailDeliverabilityAuditor
    from auditors.gbp import GBPAuditor
    from auditors.social_frequency import SocialFrequencyAuditor
    from auditors.citations import CitationsAuditor
    from engine.analyzer import InsightAnalyzer
    from engine.email_writer import EmailWriter
    from engine.email_sequence import EmailSequenceWriter
    from engine.pdf_report import generate_pdf

    audit_data = {}

    def safe_run(fn):
        try:
            return fn()
        except Exception as e:
            return {"error": str(e)}

    console.print("[dim]Running parallel audits...[/dim]")

    # ── GROUP 1: Fully independent — run all in parallel ──────────────────────
    with ThreadPoolExecutor(max_workers=9) as ex:
        futures = {
            ex.submit(safe_run, lambda: WebsiteAuditor(url).audit()): "website",
            ex.submit(safe_run, lambda: PerformanceAuditor(url).audit()): "performance",
            ex.submit(safe_run, lambda: WaybackAuditor(url).audit()): "wayback",
            ex.submit(safe_run, lambda: ReviewSentimentAuditor(business_name, url).audit()): "review_sentiment",
            ex.submit(safe_run, lambda: DNSIntelAuditor(url).audit()): "dns_intel",
            ex.submit(safe_run, lambda: TechStackAuditor(url).audit()): "tech_stack",
            ex.submit(safe_run, lambda: VisualAuditor(url, api_key).audit()): "visual",
            ex.submit(safe_run, lambda: EmailDeliverabilityAuditor(url).audit()): "email_deliverability",
        }
        for future in as_completed(futures):
            key = futures[future]
            audit_data[key] = future.result()
            console.print(f"  [green]✓[/green] {key}")

    # ── GROUP 2: Need website data — run in parallel ───────────────────────────
    website_data = audit_data.get("website", {})
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(safe_run, lambda: SEOAuditor(url, website_data).audit()): "seo",
            ex.submit(safe_run, lambda: SocialAuditor(url, website_data).audit()): "social",
            ex.submit(safe_run, lambda: ReviewAuditor(url, business_name, website_data).audit()): "reviews",
            ex.submit(safe_run, lambda: CompetitorAuditor(url, business_name, website_data).audit()): "competitors",
            ex.submit(safe_run, lambda: AdsAuditor(url, business_name, website_data).audit()): "ads",
            ex.submit(safe_run, lambda: ContentDeepAuditor(website_data).audit()): "content_deep",
            ex.submit(safe_run, lambda: GBPAuditor(business_name, url, website_data).audit()): "gbp",
            ex.submit(safe_run, lambda: SocialFrequencyAuditor(url, website_data).audit()): "social_frequency",
        }
        for future in as_completed(futures):
            key = futures[future]
            audit_data[key] = future.result()
            console.print(f"  [green]✓[/green] {key}")

    # ── GROUP 3: Need competitors for biz_type/location — run in parallel ─────
    biz_type = audit_data.get("competitors", {}).get("inferred_business_type", business_name or "business")
    location = audit_data.get("competitors", {}).get("inferred_location")

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(safe_run, lambda: TrendsAuditor(biz_type, location).audit()): "trends",
            ex.submit(safe_run, lambda: JobsAuditor(business_name, location).audit()): "jobs",
            ex.submit(safe_run, lambda: CitationsAuditor(business_name, url, location).audit()): "citations",
        }
        for future in as_completed(futures):
            key = futures[future]
            audit_data[key] = future.result()
            console.print(f"  [green]✓[/green] {key}")

    # ── GROUP 4: Need multiple modules ─────────────────────────────────────────
    audit_data["funnel"] = safe_run(lambda: FunnelAuditor(
        url,
        audit_data.get("website", {}),
        audit_data.get("performance", {}),
        audit_data.get("seo", {}),
    ).audit())
    console.print("  [green]✓[/green] funnel")

    audit_data["traffic"] = safe_run(lambda: TrafficAuditor(
        url, business_name, biz_type, audit_data
    ).audit())
    console.print("  [green]✓[/green] traffic")

    audit_data["industry"] = safe_run(lambda: IndustryAnalyzer(biz_type, audit_data).analyze())
    console.print("  [green]✓[/green] industry")

    # ── GROUP 5: AI analysis ───────────────────────────────────────────────────
    console.print("[dim]Running AI analysis...[/dim]")
    insights = safe_run(lambda: InsightAnalyzer(api_key).analyze(url, business_name, audit_data))
    console.print("  [green]✓[/green] insights")

    email = safe_run(lambda: EmailWriter(api_key).write(url, business_name, insights))
    console.print("  [green]✓[/green] cold email")

    email_sequence = safe_run(lambda: EmailSequenceWriter(api_key).write(
        url, business_name, insights, audit_data
    ))
    console.print("  [green]✓[/green] email sequence")

    # Auto-save to database
    try:
        from engine.database import AuditDatabase
        AuditDatabase().save_audit(url, business_name, audit_data, insights, email)
    except Exception:
        pass

    # Generate PDF report
    safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    pdf_path = f"report_{safe_name}.pdf"
    pdf_result = generate_pdf(pdf_path, url, business_name, audit_data, insights, email, email_sequence)

    return {
        "audit_data": audit_data,
        "insights": insights,
        "email": email,
        "email_sequence": email_sequence,
        "pdf_path": pdf_result,
    }


def batch_mode(csv_path: str, api_key: str):
    if not os.path.exists(csv_path):
        console.print(f"[red]File not found: {csv_path}[/red]")
        sys.exit(1)

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        businesses = list(reader)

    console.print(Panel(f"[bold blue]Batch Mode[/bold blue]\nProcessing {len(businesses)} businesses from {csv_path}"))

    summary_rows = []

    for i, row in enumerate(businesses, 1):
        url = normalize_url(row.get("url", "").strip())
        name = row.get("business_name", "").strip()
        console.print(f"\n[bold][{i}/{len(businesses)}][/bold] Auditing: {url}")

        try:
            result = run_single_audit(url, name, api_key)
            insights = result["insights"]
            email = result["email"]

            top = insights.get("top_insights", [{}])[0]
            summary_rows.append({
                "url": url,
                "business_name": name,
                "health_score": insights.get("overall_health_score", ""),
                "top_finding": top.get("finding", ""),
                "estimated_impact": top.get("estimated_impact", ""),
                "email_subject": email.get("subject_line", ""),
                "email_body": email.get("email", ""),
            })

            safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
            with open(f"audit_{safe_name}.json", "w") as f:
                json.dump(result, f, indent=2, default=str)

        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
            summary_rows.append({"url": url, "business_name": name, "error": str(e)})

    # Save summary CSV
    if summary_rows:
        summary_path = "batch_summary.csv"
        with open(summary_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
            writer.writeheader()
            writer.writerows(summary_rows)
        console.print(f"\n[green]Batch complete. Summary saved → {summary_path}[/green]")


def export_leads(output_path: str):
    from engine.database import AuditDatabase
    from engine.crm_export import CRMExporter
    db = AuditDatabase()
    leads = db.get_all_leads()
    CRMExporter.export_to_instantly(leads, output_path)
    console.print(f"[green]Exported {len(leads)} leads → {output_path}[/green]")


def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage:[/red]")
        console.print("  Single:  python main.py <url> [business_name]")
        console.print("  Batch:   python main.py --batch businesses.csv")
        console.print("  Export:  python main.py --export leads.csv")
        sys.exit(1)

    api_key = validate_env()

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            console.print("[red]Usage: python main.py --batch businesses.csv[/red]")
            sys.exit(1)
        batch_mode(sys.argv[2], api_key)
        return

    if sys.argv[1] == "--export":
        output = sys.argv[2] if len(sys.argv) > 2 else "leads.csv"
        export_leads(output)
        return

    url = normalize_url(sys.argv[1])
    business_name = sys.argv[2] if len(sys.argv) > 2 else None

    console.print()
    console.print(Panel(
        f"[bold blue]Business Audit AI[/bold blue]\n"
        f"[dim]Analyzing:[/dim] [yellow]{url}[/yellow]"
        + (f"\n[dim]Business:[/dim] [green]{business_name}[/green]" if business_name else ""),
        expand=False
    ))
    console.print()

    result = run_single_audit(url, business_name, api_key)
    audit_data = result["audit_data"]
    insights = result["insights"]
    email = result["email"]
    email_sequence = result.get("email_sequence", {})

    # ── OUTPUT ────────────────────────────────────────────────────────────────

    console.print()
    console.print(Panel("[bold yellow]AUDIT COMPLETE[/bold yellow]", expand=False))
    console.print()

    # Health score
    health = insights.get("overall_health_score")
    biz_summary = insights.get("business_summary", "")
    color = "green" if health and health >= 70 else "yellow" if health and health >= 50 else "red"
    console.print(f"[bold]Business:[/bold] {biz_summary}")
    console.print(f"[bold]Online Health Score:[/bold] [{color}]{health}/100[/{color}]")
    console.print()

    # Traffic estimate
    traffic = audit_data.get("traffic", {})
    if traffic.get("estimated_monthly_visitors"):
        console.print(f"[bold]Est. Monthly Visitors:[/bold] ~{traffic['estimated_monthly_visitors']:,} (confidence: {traffic.get('confidence', '?')})")
        console.print()

    # Industry score
    industry = audit_data.get("industry", {})
    if industry.get("industry_score"):
        score_info = industry["industry_score"]
        console.print(f"[bold]Industry Score:[/bold] {score_info.get('score')}/100 ({score_info.get('grade')}) — {score_info.get('must_haves_missing', 0)} must-haves missing")
        console.print()

    # Top insights table
    top_insights = insights.get("top_insights", [])
    if top_insights:
        table = Table(
            title="TOP FINDINGS & IMPACT",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold yellow",
        )
        table.add_column("#", style="bold", width=3)
        table.add_column("Finding", style="white", min_width=30)
        table.add_column("Impact", style="red", min_width=25)
        table.add_column("Urgency", style="bold", width=10)

        urgency_colors = {"critical": "red", "high": "yellow", "medium": "cyan"}

        for ins in top_insights:
            rank = str(ins.get("rank", ""))
            finding = ins.get("finding", "")
            impact = ins.get("estimated_impact", ins.get("why_it_matters", ""))
            urgency = ins.get("urgency", "medium")
            color = urgency_colors.get(urgency, "white")
            table.add_row(rank, finding, impact, f"[{color}]{urgency.upper()}[/{color}]")

        console.print(table)
        console.print()

    # Biggest opportunity
    biggest = insights.get("biggest_opportunity", "")
    if biggest:
        console.print(Panel(
            f"[bold green]{biggest}[/bold green]",
            title="[bold]BIGGEST OPPORTUNITY[/bold]",
            expand=False
        ))
        console.print()

    # Quick wins
    quick_wins = insights.get("quick_wins", [])
    if quick_wins:
        console.print("[bold]QUICK WINS:[/bold]")
        for win in quick_wins:
            console.print(f"  [green]→[/green] {win}")
        console.print()

    # Cold email
    if "email" in email:
        subject = email.get("subject_line", "")
        alt_subject = email.get("alternative_subject", "")
        email_body = email.get("email", "")

        console.print(Panel(
            f"[bold]Subject:[/bold] {subject}\n"
            + (f"[dim](alt) {alt_subject}[/dim]\n" if alt_subject else "")
            + "\n" + email_body,
            title="[bold yellow]COLD EMAIL[/bold yellow]",
            expand=True
        ))
        console.print()

    # Email sequence summary
    if email_sequence and not email_sequence.get("parse_error"):
        seq = email_sequence.get("sequence", [])
        if seq:
            console.print(Panel(
                f"[bold cyan]5-Email Sequence Generated[/bold cyan]\n"
                + "\n".join(f"  [dim]Day {e.get('send_day', '?')}:[/dim] {e.get('subject', '')}" for e in seq),
                title="[bold]EMAIL SEQUENCE[/bold]",
                expand=False
            ))
            console.print()

    # Save full report
    safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    output_path = f"audit_{safe_name}.json"
    if result.get("pdf_path"):
        console.print(f"[dim]PDF report saved → [bold]{result['pdf_path']}[/bold][/dim]")

    full_output = {
        "url": url,
        "business_name": business_name,
        "audit_data": audit_data,
        "insights": insights,
        "email": email,
        "email_sequence": email_sequence,
    }

    with open(output_path, "w") as f:
        json.dump(full_output, f, indent=2, default=str)

    console.print(f"[dim]Full audit report saved → [bold]{output_path}[/bold][/dim]")


if __name__ == "__main__":
    main()
