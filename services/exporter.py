import csv
import io

class ExporterService:
    CSV_COLUMNS = [
        "Business name",
        "Business category",
        "Business address",
        "Phone number",
        "Email address",
        "Website URL",
        "Website status",
        "Website verification status",
        "Google Maps URL",
        "Lead priority score",
        "Lead priority category",
        "Email research status",
        "Research notes",
        "Outreach status",
        "Follow up date"
    ]

    @classmethod
    def export_to_csv(cls, leads: list) -> str:
        """
        Step 9: Export the collected business information into a CSV string matching the exact 15 columns.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(cls.CSV_COLUMNS)

        for lead in leads:
            writer.writerow([
                lead.get("business_name") or "N/A",
                lead.get("business_category") or "N/A",
                lead.get("business_address") or "N/A",
                lead.get("phone_number") or "N/A",
                lead.get("email_address") or "N/A",
                lead.get("website_url") or "N/A",
                lead.get("website_status") or "N/A",
                lead.get("website_verification_status") or "N/A",
                lead.get("google_maps_url") or "N/A",
                lead.get("lead_priority_score", 0),
                lead.get("lead_priority_category") or "Low",
                lead.get("email_research_status") or "Pending",
                lead.get("research_notes") or "",
                lead.get("outreach_status") or "New",
                lead.get("follow_up_date") or ""
            ])

        return output.getvalue()
