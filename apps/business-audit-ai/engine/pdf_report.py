"""
PDF Report Generator — produces a branded, professional audit report.
Includes: health score, top findings + AI solutions, You vs Competitors table,
AI growth plan, cold email templates.

Uses reportlab (pure Python, no system dependencies).
Install: pip install reportlab
"""
import os
from datetime import datetime
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ── Color palette ──────────────────────────────────────────────────────────────
C_BLUE       = colors.HexColor("#1a73e8")
C_BLUE_DARK  = colors.HexColor("#0d47a1")
C_BLUE_LIGHT = colors.HexColor("#e8f0fe")
C_GREEN      = colors.HexColor("#1e7e34")
C_GREEN_BG   = colors.HexColor("#e6f4ea")
C_RED        = colors.HexColor("#c62828")
C_RED_BG     = colors.HexColor("#fce8e6")
C_ORANGE     = colors.HexColor("#e65100")
C_ORANGE_BG  = colors.HexColor("#fff3e0")
C_GRAY_DARK  = colors.HexColor("#212121")
C_GRAY_MID   = colors.HexColor("#757575")
C_GRAY_LIGHT = colors.HexColor("#f5f5f5")
C_BORDER     = colors.HexColor("#e0e0e0")
C_WHITE      = colors.white
C_BLACK      = colors.black


def _styles():
    base = getSampleStyleSheet()
    s = {}

    def add(name, **kw):
        s[name] = ParagraphStyle(name, parent=base["Normal"], **kw)

    add("cover_title",    fontSize=28, textColor=C_WHITE,    fontName="Helvetica-Bold",  spaceAfter=8,  alignment=TA_LEFT)
    add("cover_sub",      fontSize=13, textColor=C_BLUE_LIGHT, fontName="Helvetica",     spaceAfter=6,  alignment=TA_LEFT)
    add("section_header", fontSize=13, textColor=C_BLUE_DARK, fontName="Helvetica-Bold", spaceAfter=10, spaceBefore=6, borderPadding=(0, 0, 4, 0))
    add("body",           fontSize=9.5, textColor=C_GRAY_DARK, fontName="Helvetica",     spaceAfter=5, leading=14)
    add("body_bold",      fontSize=9.5, textColor=C_GRAY_DARK, fontName="Helvetica-Bold", spaceAfter=5, leading=14)
    add("small",          fontSize=8.5, textColor=C_GRAY_MID,  fontName="Helvetica",     spaceAfter=4)
    add("small_bold",     fontSize=8.5, textColor=C_GRAY_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    add("finding_title",  fontSize=10,  textColor=C_GRAY_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    add("impact",         fontSize=9,   textColor=C_RED,        fontName="Helvetica-Bold", spaceAfter=3)
    add("solution_title", fontSize=9.5, textColor=C_BLUE,      fontName="Helvetica-Bold", spaceAfter=3)
    add("solution_body",  fontSize=8.5, textColor=C_GRAY_MID,  fontName="Helvetica",     spaceAfter=4, leading=13)
    add("email_subject",  fontSize=10,  textColor=C_BLUE,      fontName="Helvetica-Bold", spaceAfter=6)
    add("email_body",     fontSize=9,   textColor=C_GRAY_DARK, fontName="Helvetica",     spaceAfter=6, leading=14)
    add("phase_title",    fontSize=10,  textColor=C_WHITE,     fontName="Helvetica-Bold", spaceAfter=4)
    add("table_header",   fontSize=8.5, textColor=C_WHITE,     fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("table_cell",     fontSize=8.5, textColor=C_GRAY_DARK, fontName="Helvetica",      alignment=TA_CENTER)
    add("table_row_label",fontSize=8.5, textColor=C_GRAY_DARK, fontName="Helvetica-Bold", alignment=TA_LEFT)

    return s


def _get_branding() -> dict:
    """Read white-label branding from environment variables."""
    return {
        "agency_name": os.getenv("AGENCY_NAME", "Business Audit AI"),
        "agency_tagline": os.getenv("AGENCY_TAGLINE", "AI-Powered Digital Audit"),
        "agency_email": os.getenv("AGENCY_EMAIL", ""),
        "agency_phone": os.getenv("AGENCY_PHONE", ""),
        "agency_website": os.getenv("AGENCY_WEBSITE", ""),
        "agency_logo_path": os.getenv("AGENCY_LOGO_PATH", ""),
    }


def _check(val, invert=False) -> str:
    """Return ✓ or ✗ based on truthy value."""
    if val is None:
        return "—"
    positive = bool(val)
    if invert:
        positive = not positive
    return "✓" if positive else "✗"


class PDFReportGenerator:
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab not installed. Run: pip install reportlab")

    def generate(
        self,
        output_path: str,
        url: str,
        business_name: str,
        audit_data: dict,
        insights: dict,
        email: dict,
        email_sequence: dict = None,
    ) -> str:
        S = _styles()
        story = []

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        name = business_name or url
        score = insights.get("overall_health_score", 0)
        timestamp = datetime.now().strftime("%B %d, %Y")

        # ── COVER PAGE ──────────────────────────────────────────────────────────
        story += self._cover(S, name, url, score, timestamp)
        story.append(PageBreak())

        # ── EXECUTIVE SUMMARY ───────────────────────────────────────────────────
        story += self._executive_summary(S, insights, audit_data)
        story.append(PageBreak())

        # ── YOU vs COMPETITORS ──────────────────────────────────────────────────
        comp_section = self._competitor_comparison(S, name, audit_data, insights)
        if comp_section:
            story += comp_section
            story.append(PageBreak())

        # ── TOP FINDINGS + AI SOLUTIONS ─────────────────────────────────────────
        story += self._findings_section(S, insights)
        story.append(PageBreak())

        # ── AI GROWTH PLAN ──────────────────────────────────────────────────────
        story += self._growth_plan(S, insights)

        # ── TECH STACK ──────────────────────────────────────────────────────────
        tech = audit_data.get("tech_stack", {})
        if tech.get("tools_detected"):
            story.append(PageBreak())
            story += self._tech_stack_section(S, tech)

        # ── VISUAL ANALYSIS ─────────────────────────────────────────────────────
        visual = audit_data.get("visual", {})
        if visual.get("screenshot_taken") and not visual.get("analysis", {}).get("error"):
            story.append(PageBreak())
            story += self._visual_section(S, visual)

        # ── FOOTER NOTE ─────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.3 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
        story.append(Spacer(1, 6))
        brand = _get_branding()
        footer_parts = [f"Report generated {timestamp}", f"Prepared by {brand['agency_name']}"]
        if brand["agency_website"]:
            footer_parts.append(brand["agency_website"])
        footer_parts.append("Data sourced from public signals")
        story.append(Paragraph(" · ".join(footer_parts), S["small"]))

        doc.build(story)
        return output_path

    # ── COVER ──────────────────────────────────────────────────────────────────

    def _cover(self, S, name, url, score, timestamp):
        elements = []

        # Blue header bar via a table
        score_color = "#1e7e34" if score >= 70 else "#e65100" if score >= 50 else "#c62828"
        header_data = [[
            Paragraph(f"<b>{name}</b>", ParagraphStyle("ct", fontSize=26, textColor=colors.white,
                      fontName="Helvetica-Bold")),
            Paragraph(f"<b>{score}</b><br/><font size=9>/ 100</font>",
                      ParagraphStyle("sc", fontSize=22, textColor=colors.HexColor(score_color),
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]]
        header_table = Table(header_data, colWidths=[5.2 * inch, 1.5 * inch])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 20),
            ("RIGHTPADDING", (-1, 0), (-1, 0), 20),
            ("TOPPADDING", (0, 0), (-1, -1), 20),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 16))

        # Meta row
        meta = [
            [Paragraph("<b>Website</b>", S["small_bold"]), Paragraph(url, S["small"])],
            [Paragraph("<b>Audit Date</b>", S["small_bold"]), Paragraph(timestamp, S["small"])],
            [Paragraph("<b>Report Type</b>", S["small_bold"]), Paragraph("Full Digital Presence Audit", S["small"])],
        ]
        mt = Table(meta, colWidths=[1.2 * inch, 5.5 * inch])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, C_BORDER),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        elements.append(mt)
        elements.append(Spacer(1, 20))

        # Business summary
        summary = insights_get = ""
        elements.append(Paragraph("Business Overview", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=C_BLUE))
        elements.append(Spacer(1, 8))

        return elements

    def _cover(self, S, name, url, score, timestamp):
        elements = []

        # Score color
        score_color = colors.HexColor("#1e7e34" if score >= 70 else "#e65100" if score >= 50 else "#c62828")

        # Title block
        title_data = [[
            Paragraph(name, ParagraphStyle("ct", fontSize=24, textColor=colors.white,
                                           fontName="Helvetica-Bold", leading=28)),
            Paragraph(f"<b>{score}</b><br/><font size=9 color='white'>HEALTH SCORE</font>",
                      ParagraphStyle("sc", fontSize=28, textColor=score_color,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER, leading=32)),
        ]]
        tt = Table(title_data, colWidths=[5.0 * inch, 1.7 * inch])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f1624")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 24),
            ("TOPPADDING", (0, 0), (-1, -1), 24),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
            ("RIGHTPADDING", (-1, 0), (-1, 0), 16),
        ]))
        elements.append(tt)
        elements.append(Spacer(1, 12))

        # Meta info
        elements.append(Paragraph(f"<b>Website:</b> {url}  ·  <b>Date:</b> {timestamp}  ·  <b>Type:</b> Full Digital Presence Audit", S["small"]))
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 8))

        elements.append(Paragraph("WHAT'S INSIDE THIS REPORT", S["section_header"]))
        toc_items = [
            "Executive Summary — key metrics at a glance",
            "You vs Competitors — side-by-side comparison across 10 dimensions",
            "Top 5 Findings — specific weaknesses with quantified revenue impact",
            "AI Solutions — exact systems to fix each problem with ROI estimates",
            "AI Growth Plan — 3-phase roadmap from quick wins to market dominance",
            "Tech Stack Analysis — tools you have vs tools you're missing",
        ]
        for item in toc_items:
            elements.append(Paragraph(f"• {item}", S["body"]))

        elements.append(Spacer(1, 0.25 * inch))

        # White-label branding footer on cover
        brand = _get_branding()
        brand_parts = [f"<b>{brand['agency_name']}</b>"]
        if brand["agency_website"]:
            brand_parts.append(brand["agency_website"])
        if brand["agency_email"]:
            brand_parts.append(brand["agency_email"])
        if brand["agency_phone"]:
            brand_parts.append(brand["agency_phone"])
        elements.append(Paragraph(" · ".join(brand_parts),
                                   ParagraphStyle("brand", fontSize=9, textColor=C_GRAY_MID,
                                                  fontName="Helvetica", alignment=TA_CENTER)))

        return elements

    # ── EXECUTIVE SUMMARY ──────────────────────────────────────────────────────

    def _executive_summary(self, S, insights, audit_data):
        elements = []
        elements.append(Paragraph("EXECUTIVE SUMMARY", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 10))

        biz_summary = insights.get("business_summary", "")
        if biz_summary:
            elements.append(Paragraph(biz_summary, S["body"]))
            elements.append(Spacer(1, 12))

        # Key stats grid
        score = insights.get("overall_health_score", 0)
        traffic = audit_data.get("traffic", {})
        industry = audit_data.get("industry", {})
        reviews = audit_data.get("reviews", {}).get("assessment", {})
        seo = audit_data.get("seo", {}).get("seo_score", {})
        perf = audit_data.get("performance", {}).get("summary", {})
        rev_model = industry.get("revenue_model", {})

        def stat_cell(label, value, color=None):
            val_style = ParagraphStyle("sv", fontSize=18, fontName="Helvetica-Bold",
                                       textColor=color or C_GRAY_DARK, alignment=TA_CENTER, leading=22)
            lbl_style = ParagraphStyle("sl", fontSize=7.5, fontName="Helvetica",
                                       textColor=C_GRAY_MID, alignment=TA_CENTER, leading=10)
            return [Paragraph(str(value), val_style), Paragraph(label, lbl_style)]

        score_color = colors.HexColor("#1e7e34" if score >= 70 else "#e65100" if score >= 50 else "#c62828")
        stats_data = [[
            stat_cell("Health Score", f"{score}/100", score_color),
            stat_cell("Monthly Visitors", f"~{traffic.get('estimated_monthly_visitors', '?'):,}" if isinstance(traffic.get('estimated_monthly_visitors'), int) else "?"),
            stat_cell("Google Rating", reviews.get("google_rating") or "?"),
            stat_cell("SEO Score", f"{seo.get('score', '?')}/100"),
            stat_cell("Perf Score", f"{perf.get('mobile_performance_score', '?')}"),
            stat_cell("Annual Opportunity", f"${rev_model.get('annual_revenue_opportunity', 0):,}" if isinstance(rev_model.get('annual_revenue_opportunity'), int) else "?", colors.HexColor("#1e7e34")),
        ]]
        stats_table = Table(stats_data, colWidths=[1.1 * inch] * 6)
        stats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEAFTER", (0, 0), (-2, -1), 0.5, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 16))

        # Top 3 findings summary
        top_insights = insights.get("top_insights", [])[:3]
        if top_insights:
            elements.append(Paragraph("TOP 3 CRITICAL FINDINGS", S["section_header"]))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            elements.append(Spacer(1, 8))

            for ins in top_insights:
                urg = ins.get("urgency", "medium")
                urg_color = C_RED if urg == "critical" else C_ORANGE if urg == "high" else C_BLUE
                row = [[
                    Paragraph(f"<b>{ins.get('rank')}. {ins.get('title', '')}</b>", S["finding_title"]),
                    Paragraph(urg.upper(), ParagraphStyle("urg", fontSize=7.5, textColor=C_WHITE,
                              fontName="Helvetica-Bold", alignment=TA_CENTER)),
                ]]
                rt = Table(row, colWidths=[5.8 * inch, 0.8 * inch])
                rt.setStyle(TableStyle([
                    ("BACKGROUND", (1, 0), (1, 0), urg_color),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (-1, 0), (-1, 0), 0),
                ]))
                elements.append(rt)
                elements.append(Paragraph(ins.get("finding", ""), S["body"]))
                elements.append(Paragraph(f"Impact: {ins.get('estimated_impact', '')}", S["impact"]))
                elements.append(Spacer(1, 8))

        # Total opportunity callout
        opp = insights.get("total_ai_opportunity")
        if opp:
            opp_data = [[Paragraph(f"<b>Total AI Opportunity:</b> {opp}", S["body"])]]
            ot = Table(opp_data, colWidths=[6.65 * inch])
            ot.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_GREEN_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEAFTER", (0, 0), (0, 0), 4, C_GREEN),
            ]))
            elements.append(ot)

        return elements

    # ── COMPETITOR COMPARISON ──────────────────────────────────────────────────

    def _competitor_comparison(self, S, business_name, audit_data, insights):
        comp_data = audit_data.get("competitors", {})
        # Use 'comparison' which has the enriched site data (has_blog, rating, etc.)
        # Fall back to competitors_found if comparison not available
        competitors = comp_data.get("comparison") or comp_data.get("competitors_found", [])
        if not competitors:
            return []

        elements = []
        elements.append(Paragraph("YOU vs COMPETITORS", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "Side-by-side comparison across key digital presence dimensions. "
            "✓ = present / ✗ = missing / — = unknown",
            S["small"]
        ))
        elements.append(Spacer(1, 10))

        reviews_data = audit_data.get("reviews", {}).get("assessment", {})
        website_data = audit_data.get("website", {})
        seo_data = audit_data.get("seo", {})
        perf_data = audit_data.get("performance", {}).get("summary", {})
        social_data = audit_data.get("social", {})
        conv = website_data.get("conversion_signals", {})
        trust = website_data.get("trust_signals", {})
        content = website_data.get("content_signals", {})

        # We audit the target business — build its profile
        target = {
            "name": business_name or "Your Business",
            "rating": reviews_data.get("google_rating"),
            "review_count": reviews_data.get("google_review_count"),
            "has_blog": bool(content.get("has_blog")),
            "has_live_chat": bool(website_data.get("global_signals", {}).get("has_live_chat")),
            "has_booking": bool(conv.get("booking_system")),
            "has_free_offer": bool(conv.get("has_free_offer")),
            "social_count": social_data.get("platform_count", 0),
            "has_video": bool(website_data.get("global_signals", {}).get("has_video_content")),
            "perf_score": perf_data.get("mobile_performance_score"),
            "seo_score": seo_data.get("seo_score", {}).get("score"),
            "has_cta": bool(conv.get("above_fold_cta")),
        }

        # Headers
        comp_names = [c.get("name", f"Competitor {i+1}")[:18] for i, c in enumerate(competitors[:3])]
        header_row = [
            Paragraph("Metric", S["table_header"]),
            Paragraph(target["name"][:20], ParagraphStyle("th_you", fontSize=8.5, textColor=colors.white,
                       fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ] + [Paragraph(n, S["table_header"]) for n in comp_names]

        # Rows
        def make_row(label, you_val, comp_vals, is_number=False):
            def fmt(v):
                if v is None:
                    return Paragraph("—", S["table_cell"])
                if is_number:
                    return Paragraph(str(v), S["table_cell"])
                color = C_GREEN if v else C_RED
                text = "✓" if v else "✗"
                return Paragraph(text, ParagraphStyle("cc", fontSize=9, textColor=color,
                                                       fontName="Helvetica-Bold", alignment=TA_CENTER))

            you_cell = fmt(you_val) if not is_number else Paragraph(
                str(you_val) if you_val is not None else "—", S["table_cell"])

            return [Paragraph(label, S["table_row_label"]), you_cell] + [fmt(v) for v in comp_vals]

        rows = [header_row]
        comp_list = competitors[:3]

        rows.append(make_row("Google Rating",
            target["rating"],
            [c.get("rating") for c in comp_list], is_number=True))

        rows.append(make_row("Review Count",
            target["review_count"],
            [c.get("review_count") for c in comp_list], is_number=True))

        rows.append(make_row("Has Blog",
            target["has_blog"],
            [c.get("has_blog") for c in comp_list]))

        rows.append(make_row("Live Chat",
            target["has_live_chat"],
            [c.get("has_live_chat") for c in comp_list]))

        rows.append(make_row("Online Booking",
            target["has_booking"],
            [c.get("has_booking") for c in comp_list]))

        rows.append(make_row("Free Offer/Lead Magnet",
            target["has_free_offer"],
            [c.get("has_free_offer") for c in comp_list]))

        rows.append(make_row("Video Content",
            target["has_video"],
            [c.get("has_video") for c in comp_list]))

        rows.append(make_row("Above-Fold CTA",
            target["has_cta"],
            [None for _ in comp_list]))

        def comp_social_count(c):
            sp = c.get("social_platforms")
            if sp is None:
                return None
            if isinstance(sp, list):
                return len(sp)
            if isinstance(sp, int):
                return sp
            return None

        rows.append(make_row("Social Platforms",
            target["social_count"],
            [comp_social_count(c) for c in comp_list],
            is_number=True))

        rows.append(make_row("Mobile Perf Score",
            target["perf_score"],
            [None for _ in comp_list], is_number=True))

        n_cols = 2 + len(comp_names)
        col_w = 6.65 * inch / n_cols
        first_col_w = 1.7 * inch
        other_col_w = (6.65 * inch - first_col_w) / (n_cols - 1)
        col_widths = [first_col_w] + [other_col_w] * (n_cols - 1)

        table = Table(rows, colWidths=col_widths, repeatRows=1)

        style = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f1624")),
            ("BACKGROUND", (1, 0), (1, 0), C_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            # Data rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
            ("BACKGROUND", (1, 1), (1, -1), C_BLUE_LIGHT),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, C_BLUE),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        table.setStyle(TableStyle(style))
        elements.append(table)

        # Gaps summary
        gaps = comp_data.get("gaps", {}).get("gaps_vs_competitors", [])
        if gaps:
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Key Competitive Gaps:", S["body_bold"]))
            for gap in gaps[:4]:
                elements.append(Paragraph(f"• {gap}", S["body"]))

        return elements

    # ── FINDINGS ───────────────────────────────────────────────────────────────

    def _findings_section(self, S, insights):
        elements = []
        elements.append(Paragraph("TOP FINDINGS + AI SOLUTIONS", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 10))

        top_insights = insights.get("top_insights", [])

        # Show parse error if AI analysis failed
        if not top_insights:
            err = insights.get("parse_error") or insights.get("_tier3_error") or "AI analysis returned no findings."
            elements.append(Paragraph(
                f"AI analysis did not return findings for this audit. Raw error: {err}",
                ParagraphStyle("err", fontSize=9, textColor=C_RED, fontName="Helvetica")
            ))
            return elements

        for ins in top_insights:
            urg = ins.get("urgency", "medium")
            urg_color = C_RED if urg == "critical" else C_ORANGE if urg == "high" else C_BLUE
            urg_bg = C_RED_BG if urg == "critical" else C_ORANGE_BG if urg == "high" else C_BLUE_LIGHT
            sol = ins.get("ai_solution", {})

            block = []

            # Finding header
            header_data = [[
                Paragraph(f"{ins.get('rank')}. {ins.get('title', '')}", S["finding_title"]),
                Paragraph(urg.upper(), ParagraphStyle("ut", fontSize=7.5, textColor=C_WHITE,
                          fontName="Helvetica-Bold", alignment=TA_CENTER)),
            ]]
            ht = Table(header_data, colWidths=[5.8 * inch, 0.85 * inch])
            ht.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), urg_bg),
                ("BACKGROUND", (1, 0), (1, 0), urg_color),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (0, 0), 10),
            ]))
            block.append(ht)

            # Finding body
            body_data = [
                [Paragraph(ins.get("finding", ""), S["body"])],
                [Paragraph(f"💰 {ins.get('estimated_impact', '')}", S["impact"])],
            ]
            if ins.get("benchmark"):
                body_data.append([Paragraph(f"Benchmark: {ins.get('benchmark')}", S["small"])])
            if ins.get("citation"):
                cite_style = ParagraphStyle("cite", fontSize=7.5, textColor=C_GRAY_MID,
                                            fontName="Helvetica-Oblique")
                body_data.append([Paragraph(f"Source: {ins['citation']}", cite_style)])

            # Confidence badge + fix simulation
            conf = ins.get("confidence", {})
            sim = ins.get("fix_simulation", {})
            conf_level = conf.get("level", "")
            conf_note = conf.get("confidence_note", "")
            if conf_level:
                conf_colors_map = {"HIGH": C_GREEN, "MEDIUM": C_ORANGE, "LOW": C_GRAY_MID, "ESTIMATED": C_GRAY_MID}
                conf_color = conf_colors_map.get(conf_level, C_GRAY_MID)
                conf_style = ParagraphStyle("conf", fontSize=7.5, textColor=conf_color,
                                            fontName="Helvetica-Bold")
                note_style = ParagraphStyle("confn", fontSize=7.5, textColor=C_GRAY_MID, fontName="Helvetica")
                body_data.append([Paragraph(f"Confidence: {conf_level}  |  {conf_note}", conf_style)])

            if sim.get("conservative_estimate"):
                sim_style = ParagraphStyle("sim", fontSize=8, textColor=colors.HexColor("#1565c0"),
                                           fontName="Helvetica-Bold")
                sim_body = ParagraphStyle("simb", fontSize=7.5, textColor=C_GRAY_MID, fontName="Helvetica")
                body_data.append([Paragraph("Fix Simulation (cited projections):", sim_style)])
                body_data.append([Paragraph(
                    f"Conservative: {sim['conservative_estimate']}  |  "
                    f"Realistic: {sim.get('realistic_estimate', '—')}",
                    sim_body
                )])
                if sim.get("citation"):
                    body_data.append([Paragraph(f"Basis: {sim['citation']}", ParagraphStyle(
                        "simcite", fontSize=7, textColor=C_GRAY_MID, fontName="Helvetica-Oblique"
                    ))])

            body_t = Table(body_data, colWidths=[6.65 * inch])
            body_t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            block.append(body_t)

            # AI Solution box
            if sol.get("name"):
                sol_content = [
                    [Paragraph(f"⚡  {sol['name']}", S["solution_title"])],
                    [Paragraph(sol.get("what_it_does", ""), S["solution_body"])],
                    [Paragraph(sol.get("how_it_works", ""), S["small"])],
                ]
                details = []
                if sol.get("timeline"):
                    details.append(f"⏱ {sol['timeline']}")
                if sol.get("specific_outcome"):
                    details.append(f"📈 {sol['specific_outcome']}")
                if sol.get("monthly_roi"):
                    details.append(f"💰 {sol['monthly_roi']}")
                if details:
                    sol_content.append([Paragraph("   ".join(details),
                                        ParagraphStyle("det", fontSize=8.5, textColor=C_GREEN,
                                                       fontName="Helvetica-Bold"))])

                sol_t = Table(sol_content, colWidths=[6.65 * inch])
                sol_t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f0fe")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, C_BLUE),
                ]))
                block.append(sol_t)

            elements.append(KeepTogether(block))
            elements.append(Spacer(1, 14))

        return elements

    # ── GROWTH PLAN ────────────────────────────────────────────────────────────

    def _growth_plan(self, S, insights):
        elements = []
        elements.append(Paragraph("AI GROWTH PLAN", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 10))

        if not insights.get("ai_growth_plan"):
            elements.append(Paragraph("Growth plan not available — AI analysis did not return phase data.", S["small"]))
            return elements

        phase_colors = [
            colors.HexColor("#1565c0"),
            colors.HexColor("#e65100"),
            colors.HexColor("#1b5e20"),
        ]

        for i, phase in enumerate(insights.get("ai_growth_plan", [])):
            pc = phase_colors[i % len(phase_colors)]
            bg = colors.HexColor(["#e3f2fd", "#fff3e0", "#e8f5e9"][i % 3])

            phase_data = [
                [Paragraph(phase.get("name", f"Phase {i+1}"), S["phase_title"])],
                [Paragraph(phase.get("combined_impact", ""), S["solution_body"])],
                [Paragraph("Solutions: " + ", ".join(phase.get("solutions", [])), S["small"])],
            ]
            if phase.get("estimated_monthly_value"):
                phase_data.append([Paragraph(phase["estimated_monthly_value"],
                                  ParagraphStyle("pv", fontSize=10, textColor=pc,
                                                 fontName="Helvetica-Bold"))])

            header_row = [[Paragraph(phase.get("name", f"Phase {i+1}"), S["phase_title"])]]
            ht = Table(header_row, colWidths=[6.65 * inch])
            ht.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), pc),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))

            body_rows = phase_data[1:]
            bt = Table(body_rows, colWidths=[6.65 * inch])
            bt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))

            elements.append(KeepTogether([ht, bt]))
            elements.append(Spacer(1, 10))

        return elements

    # ── TECH STACK ─────────────────────────────────────────────────────────────

    def _tech_stack_section(self, S, tech_data):
        elements = []
        elements.append(Paragraph("TECH STACK ANALYSIS", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 8))

        soph = tech_data.get("sophistication_score", {})
        elements.append(Paragraph(
            f"<b>{soph.get('tool_count', 0)} tools detected</b> · Grade: <b>{soph.get('grade', '?')}</b> · "
            f"Missing critical categories: <b>{soph.get('missing_critical_categories', 0)}</b>",
            S["body"]
        ))
        elements.append(Spacer(1, 8))

        # Tools by category
        categories = tech_data.get("categories", {})
        if categories:
            cat_rows = [[
                Paragraph("Category", S["table_header"]),
                Paragraph("Tools Detected", S["table_header"]),
            ]]
            for cat, tools in sorted(categories.items()):
                cat_rows.append([
                    Paragraph(cat, S["table_row_label"]),
                    Paragraph(", ".join(tools), S["table_cell"]),
                ])
            ct = Table(cat_rows, colWidths=[1.8 * inch, 4.85 * inch])
            ct.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f1624")),
                ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_GRAY_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elements.append(ct)
            elements.append(Spacer(1, 10))

        # Gaps
        gaps = tech_data.get("gaps", [])
        if gaps:
            elements.append(Paragraph("Missing Tool Categories (AI Opportunities):", S["body_bold"]))
            for gap in gaps[:5]:
                elements.append(Paragraph(f"• <b>{gap['missing_category']}:</b> {gap['cold_email_angle']}", S["body"]))

        return elements

    # ── VISUAL SECTION ─────────────────────────────────────────────────────────

    def _visual_section(self, S, visual_data):
        elements = []
        elements.append(Paragraph("AI VISUAL ANALYSIS", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "Screenshot analyzed by AI vision model — catches design problems no code scanner can find.",
            S["small"]
        ))
        elements.append(Spacer(1, 10))

        a = visual_data.get("analysis", {})
        score = visual_data.get("overall_score", 0)
        grade = visual_data.get("overall_grade", "?")
        score_color = colors.HexColor("#1e7e34" if score >= 70 else "#e65100" if score >= 50 else "#c62828")

        # Score grid
        stat_rows = [[
            Paragraph(f"<b>{grade}</b>", ParagraphStyle("vg", fontSize=20, textColor=score_color,
                      fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(str(score), ParagraphStyle("vs", fontSize=20, textColor=score_color,
                      fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(str(visual_data.get("design_era", "?")),
                      ParagraphStyle("de", fontSize=10, textColor=C_GRAY_DARK,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("Yes" if visual_data.get("cta_above_fold") else "No",
                      ParagraphStyle("cta", fontSize=14, alignment=TA_CENTER, fontName="Helvetica-Bold",
                                     textColor=colors.HexColor("#1e7e34") if visual_data.get("cta_above_fold") else C_RED)),
            Paragraph(str(a.get("visual_clutter", "?")),
                      ParagraphStyle("vc", fontSize=10, textColor=C_GRAY_DARK,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]]
        labels = [["Visual Grade"], ["Score / 100"], ["Design Era"], ["CTA Above Fold"], ["Clutter"]]
        lbl_style = ParagraphStyle("lbl", fontSize=7.5, textColor=C_GRAY_MID,
                                    fontName="Helvetica", alignment=TA_CENTER)

        combined = [[stat_rows[0][i], Paragraph(labels[i][0], lbl_style)] for i in range(5)]
        # Build as a simple table
        grid_data = [stat_rows[0], [Paragraph(l[0], lbl_style) for l in labels]]
        gt = Table(grid_data, colWidths=[1.33 * inch] * 5)
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEAFTER", (0, 0), (-2, -1), 0.5, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(gt)
        elements.append(Spacer(1, 12))

        # Headline seen
        if a.get("headline_text"):
            elements.append(Paragraph(f'Headline detected: <i>"{a["headline_text"]}"</i>', S["small"]))
            elements.append(Spacer(1, 8))

        # Top issues
        issues = visual_data.get("top_issues", [])
        if issues:
            elements.append(Paragraph("Specific Visual Problems Found:", S["body_bold"]))
            for issue in issues:
                issue_data = [[Paragraph(issue, S["body"])]]
                it = Table(issue_data, colWidths=[6.65 * inch])
                it.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), C_RED_BG),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, C_RED),
                ]))
                elements.append(it)
                elements.append(Spacer(1, 4))

        # Most urgent fix
        if a.get("most_urgent_fix"):
            elements.append(Spacer(1, 8))
            fix_data = [[Paragraph(f"<b>Most urgent fix:</b> {a['most_urgent_fix']}", S["body"])]]
            ft = Table(fix_data, colWidths=[6.65 * inch])
            ft.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_GREEN_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LINEBEFORE", (0, 0), (0, -1), 3, C_GREEN),
            ]))
            elements.append(ft)

        # Cold email angle
        if visual_data.get("cold_email_angle"):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(
                f'Cold email angle: <i>"{visual_data["cold_email_angle"]}"</i>',
                ParagraphStyle("cea", fontSize=9, textColor=C_BLUE, fontName="Helvetica-Oblique")
            ))

        return elements

    # ── EMAIL SECTION ──────────────────────────────────────────────────────────

    def _email_section(self, S, email, email_sequence):
        elements = []
        elements.append(Paragraph("COLD EMAIL TEMPLATES", S["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE))
        elements.append(Spacer(1, 8))

        # Single email
        if email.get("email"):
            subj_data = [[Paragraph(f"Subject: {email.get('subject_line', '')}", S["email_subject"])]]
            st = Table(subj_data, colWidths=[6.65 * inch])
            st.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_BLUE_LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBEFORE", (0, 0), (0, -1), 3, C_BLUE),
            ]))
            elements.append(st)
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(email["email"], S["email_body"]))
            elements.append(Spacer(1, 16))

        # Sequence
        seq = (email_sequence or {}).get("sequence", [])
        if seq:
            elements.append(Paragraph("5-EMAIL OUTREACH SEQUENCE", S["section_header"]))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            elements.append(Spacer(1, 8))

            seq_colors = [C_BLUE, colors.HexColor("#7b1fa2"), C_GREEN,
                          C_ORANGE, colors.HexColor("#c62828")]

            for i, em in enumerate(seq):
                day_label = "Send Today" if em.get("send_day") == 0 else f"Send Day {em.get('send_day', i*3)}"
                pc = seq_colors[i % len(seq_colors)]

                header = [[
                    Paragraph(f"Email {em.get('email_number', i+1)} — {day_label}", S["phase_title"]),
                    Paragraph(em.get("angle", ""), ParagraphStyle("angle", fontSize=7.5,
                              textColor=C_WHITE, fontName="Helvetica", alignment=TA_RIGHT)),
                ]]
                ht = Table(header, colWidths=[3.5 * inch, 3.15 * inch])
                ht.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), pc),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))

                body_rows = [
                    [Paragraph(f"Subject: {em.get('subject', '')}", S["email_subject"])],
                    [Paragraph(em.get("body", ""), S["email_body"])],
                ]
                bt = Table(body_rows, colWidths=[6.65 * inch])
                bt.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), C_GRAY_LIGHT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, pc),
                ]))

                elements.append(KeepTogether([ht, bt]))
                elements.append(Spacer(1, 10))

        return elements


def generate_pdf(output_path: str, url: str, business_name: str,
                 audit_data: dict, insights: dict, email: dict,
                 email_sequence: dict = None) -> Optional[str]:
    """Convenience wrapper. Returns path on success, None on failure."""
    try:
        gen = PDFReportGenerator()
        return gen.generate(output_path, url, business_name, audit_data, insights, email, email_sequence)
    except ImportError:
        print("PDF generation requires reportlab: pip install reportlab")
        return None
    except Exception as e:
        print(f"PDF generation failed: {e}")
        return None
