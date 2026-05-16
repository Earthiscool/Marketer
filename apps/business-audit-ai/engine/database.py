"""
Audit Database — SQLite storage for audit history, change tracking,
and CRM pipeline management.
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audits.db")


class AuditDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    business_name TEXT,
                    timestamp TEXT NOT NULL,
                    health_score INTEGER,
                    audit_data_json TEXT,
                    insights_json TEXT,
                    email_text TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_name TEXT,
                    url TEXT UNIQUE NOT NULL,
                    email TEXT,
                    phone TEXT,
                    industry TEXT,
                    location TEXT,
                    lead_score INTEGER,
                    hook TEXT,
                    offer TEXT,
                    next_step TEXT,
                    next_follow_up TEXT,
                    status TEXT DEFAULT 'new',
                    health_score INTEGER,
                    top_finding TEXT,
                    email_subject TEXT,
                    email_body TEXT,
                    last_contact TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            self._ensure_columns(conn)
            conn.commit()

    def _ensure_columns(self, conn):
        existing = {row[1] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
        columns = {
            "phone": "TEXT",
            "industry": "TEXT",
            "location": "TEXT",
            "lead_score": "INTEGER",
            "hook": "TEXT",
            "offer": "TEXT",
            "next_step": "TEXT",
            "next_follow_up": "TEXT",
        }
        for name, col_type in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {name} {col_type}")

    def save_audit(self, url: str, business_name: str, audit_data: dict, insights: dict, email: dict) -> int:
        health_score = insights.get("overall_health_score")
        top_insights = insights.get("top_insights", [])
        top_finding = top_insights[0].get("finding", "") if top_insights else ""
        email_subject = email.get("subject_line", "")
        email_body = email.get("email", "")
        timestamp = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO audits (url, business_name, timestamp, health_score, audit_data_json, insights_json, email_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                url,
                business_name,
                timestamp,
                health_score,
                json.dumps(audit_data, default=str),
                json.dumps(insights, default=str),
                email_body,
            ))
            audit_id = cursor.lastrowid

            # Upsert into leads table
            contact = self._extract_contact(audit_data)
            conn.execute("""
                INSERT INTO leads (
                    business_name, url, email, phone, health_score, top_finding,
                    email_subject, email_body, status, next_step, next_follow_up, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', 'Send permission email', ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    email = COALESCE(excluded.email, leads.email),
                    phone = COALESCE(excluded.phone, leads.phone),
                    health_score = excluded.health_score,
                    top_finding = excluded.top_finding,
                    email_subject = excluded.email_subject,
                    email_body = excluded.email_body,
                    next_step = COALESCE(leads.next_step, excluded.next_step),
                    next_follow_up = COALESCE(leads.next_follow_up, excluded.next_follow_up)
            """, (
                business_name, url, contact.get("email"), contact.get("phone"),
                health_score, top_finding, email_subject, email_body,
                (datetime.utcnow() + timedelta(days=1)).date().isoformat(), timestamp,
            ))

            conn.commit()
        return audit_id

    def save_sales_pack(self, pack: dict):
        row = pack.get("crm_row", {})
        if not row.get("url"):
            return
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO leads (
                    business_name, url, email, phone, industry, location, lead_score,
                    hook, offer, next_step, status, next_follow_up, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    business_name = COALESCE(excluded.business_name, leads.business_name),
                    email = COALESCE(excluded.email, leads.email),
                    phone = COALESCE(excluded.phone, leads.phone),
                    industry = COALESCE(excluded.industry, leads.industry),
                    location = COALESCE(excluded.location, leads.location),
                    lead_score = excluded.lead_score,
                    hook = excluded.hook,
                    offer = excluded.offer,
                    next_step = excluded.next_step
            """, (
                row.get("business_name"), row.get("url"), row.get("email"),
                row.get("phone"), row.get("industry"), row.get("location"),
                row.get("lead_score"), row.get("hook"), row.get("offer"),
                row.get("next_step"), row.get("status", "new"),
                (datetime.utcnow() + timedelta(days=1)).date().isoformat(), now,
            ))
            conn.commit()

    def add_prospect(self, prospect: dict):
        now = datetime.utcnow().isoformat()
        url = prospect.get("url")
        if not url:
            return
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO leads (
                    business_name, url, email, phone, industry, location,
                    lead_score, hook, offer, next_step, status, next_follow_up, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'found', ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    business_name = COALESCE(excluded.business_name, leads.business_name),
                    industry = COALESCE(excluded.industry, leads.industry),
                    location = COALESCE(excluded.location, leads.location),
                    notes = COALESCE(leads.notes, excluded.notes)
            """, (
                prospect.get("business_name"), url, prospect.get("email"),
                prospect.get("phone"), prospect.get("industry"), prospect.get("location"),
                prospect.get("lead_score", 45), prospect.get("hook"),
                prospect.get("offer", "AI lead follow-up pilot"),
                prospect.get("next_step", "Run audit"),
                datetime.utcnow().date().isoformat(),
                prospect.get("source"), now,
            ))
            conn.commit()

    def get_audit_history(self, url: str) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, health_score, insights_json
                FROM audits WHERE url = ?
                ORDER BY timestamp DESC
            """, (url,)).fetchall()
        return [
            {"id": r[0], "timestamp": r[1], "health_score": r[2], "insights": json.loads(r[3] or "{}")}
            for r in rows
        ]

    def get_all_leads(self) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT business_name, url, email, status, health_score,
                       top_finding, email_subject, email_body, last_contact, notes, created_at,
                       phone, industry, location, lead_score, hook, offer, next_step, next_follow_up
                FROM leads
                ORDER BY COALESCE(lead_score, 0) DESC, COALESCE(health_score, 999) ASC
            """).fetchall()
        return [
            {
                "business_name": r[0], "url": r[1], "email": r[2], "status": r[3],
                "health_score": r[4], "top_finding": r[5], "email_subject": r[6],
                "email_body": r[7], "last_contact": r[8], "notes": r[9], "created_at": r[10],
                "phone": r[11], "industry": r[12], "location": r[13], "lead_score": r[14],
                "hook": r[15], "offer": r[16], "next_step": r[17], "next_follow_up": r[18],
            }
            for r in rows
        ]

    def get_due_leads(self) -> list:
        today = datetime.utcnow().date().isoformat()
        return [
            lead for lead in self.get_all_leads()
            if not lead.get("next_follow_up") or lead.get("next_follow_up") <= today
        ]

    def update_lead_status(self, url: str, status: str, notes: str = None, next_follow_up: str = None, next_step: str = None):
        with self._connect() as conn:
            conn.execute("""
                UPDATE leads
                SET status = ?,
                    last_contact = ?,
                    notes = COALESCE(?, notes),
                    next_follow_up = COALESCE(?, next_follow_up),
                    next_step = COALESCE(?, next_step)
                WHERE url = ?
            """, (status, datetime.utcnow().isoformat(), notes, next_follow_up, next_step, url))
            conn.commit()

    def _extract_contact(self, audit_data: dict) -> dict:
        website = audit_data.get("website", {})
        homepage = website.get("homepage", {})
        pages = website.get("internal_pages", {})

        emails = list(homepage.get("email_addresses") or [])
        phones = list(homepage.get("phone_numbers") or [])
        for page in pages.values():
            emails.extend(page.get("email_addresses") or [])
            phones.extend(page.get("phone_numbers") or [])

        return {
            "email": emails[0] if emails else None,
            "phone": phones[0] if phones else None,
        }
