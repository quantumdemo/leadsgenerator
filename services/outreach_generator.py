class OutreachGeneratorService:
    @staticmethod
    def generate_email_draft(business_name: str, category: str, address: str, website_status: str) -> dict:
        """
        Step 11: Generate personalised outreach email drafts tailored to business category and website status.
        """
        cat_lower = (category or "").lower()

        # Category specific tailored pitch
        if "restaurant" in cat_lower or "cafe" in cat_lower or "food" in cat_lower:
            value_pitch = "an interactive online menu, direct WhatsApp reservation booking, and automated customer table inquiries"
        elif "repair" in cat_lower or "workshop" in cat_lower or "auto" in cat_lower:
            value_pitch = "a digital service catalog, instant online quote request form, and direct WhatsApp booking for vehicle diagnostics"
        elif "hotel" in cat_lower or "guest" in cat_lower or "lodge" in cat_lower:
            value_pitch = "a direct room booking showcase to eliminate third-party commission fees and display high-res room galleries"
        else:
            value_pitch = "a professional high-converting website featuring your service portfolio, customer testimonials, and direct WhatsApp booking buttons"

        if website_status == "No website listed":
            observation = f"I noticed that {business_name} has a strong presence on Google Maps, but currently does not have an official website listed."
        elif website_status == "Website unavailable or inaccessible":
            observation = f"I noticed that the website listed on Google Maps for {business_name} currently appears to be inaccessible or returning errors."
        else:
            observation = f"I noticed {business_name} on Google Maps and wanted to share how a modernized web platform could boost your client bookings."

        subject = f"Website Development & Digital Growth Proposal for {business_name}"

        body = f"""Hello Team {business_name},

{observation}

At AfixTech, we specialize in building fast, mobile-friendly websites designed to convert local searches into paying customers.

For a business like yours in {address or 'your area'}, a modern web presence with {value_pitch} can significantly increase your daily customer inquiries and build trust with new clients.

Would you be open to a quick 5-minute call or WhatsApp chat to discuss how we can create a custom site for {business_name}?

Best regards,

The AfixTech Development Team
Email: contact@afixtech.com | Website: https://afixtech.com
"""

        return {
            "subject": subject,
            "body": body
        }
