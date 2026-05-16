"""
CRM Export — exports audit results in Instantly.ai / Apollo.io cold email format.
"""
import csv
from datetime import datetime


class CRMExporter:
    @staticmethod
    def export_to_instantly(leads: list, filename: str):
        """Export leads in Instantly.ai import format."""
        if not leads:
            print("No leads to export.")
            return

        fieldnames = [
            "firstName", "lastName", "email", "companyName", "website",
            "customVariable1",  # health_score
            "customVariable2",  # top_finding
            "customVariable3",  # email_subject
            "emailBody",
        ]

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for lead in leads:
                biz_name = lead.get("business_name") or ""
                parts = biz_name.split(" ", 1)
                first = parts[0] if parts else ""
                last = parts[1] if len(parts) > 1 else ""

                writer.writerow({
                    "firstName": first,
                    "lastName": last,
                    "email": lead.get("email") or "",
                    "companyName": biz_name,
                    "website": lead.get("url") or "",
                    "customVariable1": lead.get("health_score") or "",
                    "customVariable2": lead.get("top_finding") or "",
                    "customVariable3": lead.get("email_subject") or "",
                    "emailBody": lead.get("email_body") or "",
                })

        print(f"Exported {len(leads)} leads → {filename}")

    @staticmethod
    def export_to_apollo(leads: list, filename: str):
        """Export leads in Apollo.io import format."""
        if not leads:
            return

        fieldnames = [
            "Company Name", "Website", "Person Name", "Email",
            "Custom Field: Health Score", "Custom Field: Top Finding",
            "Email Subject", "Email Body", "Notes",
        ]

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for lead in leads:
                writer.writerow({
                    "Company Name": lead.get("business_name") or "",
                    "Website": lead.get("url") or "",
                    "Person Name": lead.get("business_name") or "",
                    "Email": lead.get("email") or "",
                    "Custom Field: Health Score": lead.get("health_score") or "",
                    "Custom Field: Top Finding": lead.get("top_finding") or "",
                    "Email Subject": lead.get("email_subject") or "",
                    "Email Body": lead.get("email_body") or "",
                    "Notes": lead.get("notes") or "",
                })

        print(f"Exported {len(leads)} leads (Apollo format) → {filename}")
