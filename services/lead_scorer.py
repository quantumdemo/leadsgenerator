class LeadScorerService:
    HIGH_VALUE_CATEGORIES = [
        "restaurant", "hotel", "car_repair", "auto_repair", "workshop",
        "bar", "cafe", "guest_house", "real_estate", "law_firm", "dental", "clinic"
    ]

    @classmethod
    def score_lead(cls, business_data: dict) -> dict:
        """
        Step 7: Score and prioritise leads (0 to 100 points).
        Considers website need, contact info availability, business activity, and service match.
        """
        score = 0
        reasons = []

        website_status = business_data.get("website_status", "")
        has_email = bool(business_data.get("email_address"))
        has_phone = bool(business_data.get("phone_number"))
        ratings_count = business_data.get("user_ratings_total", 0) or 0
        rating = business_data.get("rating", 0.0) or 0.0
        category = (business_data.get("business_category") or "").lower()

        # 1. Website Need (Max 40 points)
        if website_status == "No website listed":
            score += 40
            reasons.append("No website listed (+40)")
        elif website_status == "Website unavailable or inaccessible":
            score += 35
            reasons.append("Website is broken/inaccessible (+35)")
        elif website_status == "Website requires verification":
            score += 20
            reasons.append("Website unverified (+20)")

        # 2. Contact Information Quality (Max 30 points)
        if has_email:
            score += 15
            reasons.append("Direct email available (+15)")
        if has_phone:
            score += 15
            reasons.append("Phone number available (+15)")

        # 3. Business Activity & Readiness (Max 20 points)
        if ratings_count > 10:
            score += 10
            reasons.append("Established activity (>10 reviews) (+10)")
        if rating >= 4.0:
            score += 10
            reasons.append("High customer rating (≥4.0) (+10)")

        # 4. Target Industry Match for AfixTech (Max 10 points)
        if any(cat in category for cat in cls.HIGH_VALUE_CATEGORIES):
            score += 10
            reasons.append("High-converting business category (+10)")

        # Categorize Priority Tier
        if score >= 70:
            category_tier = "High"
        elif score >= 40:
            category_tier = "Medium"
        else:
            category_tier = "Low"

        return {
            "lead_priority_score": score,
            "lead_priority_category": category_tier,
            "scoring_reasons": "; ".join(reasons)
        }
