import os

# Ensure dotenv is loaded if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from database import db, get_database_uri
from models import Lead
from services.google_maps import GooglePlacesService
from services.website_crawler import WebsiteCrawlerService
from services.website_verifier import WebsiteVerifierService
from services.lead_scorer import LeadScorerService
from services.outreach_generator import OutreachGeneratorService
from services.exporter import ExporterService

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "afixtech_lead_finder_secret")

# Check DATABASE_URL configuration
db_error_message = None
try:
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
except Exception as e:
    db_error_message = str(e)

@app.context_processor
def inject_config_status():
    has_api_key = bool(os.getenv("GOOGLE_PLACES_API_KEY") and os.getenv("GOOGLE_PLACES_API_KEY") != "your_google_places_api_key_here")
    has_db = db_error_message is None
    return dict(has_api_key=has_api_key, has_db=has_db, db_error_message=db_error_message)

@app.route("/")
def dashboard():
    if db_error_message:
        return render_template("dashboard.html", db_error=db_error_message, leads=[], stats={})

    query_filter = request.args.get("query", "").strip()
    priority_filter = request.args.get("priority", "").strip()
    status_filter = request.args.get("status", "").strip()

    leads_query = Lead.query

    if query_filter:
        leads_query = leads_query.filter(
            (Lead.business_name.ilike(f"%{query_filter}%")) |
            (Lead.business_category.ilike(f"%{query_filter}%")) |
            (Lead.business_address.ilike(f"%{query_filter}%"))
        )
    if priority_filter:
        leads_query = leads_query.filter(Lead.lead_priority_category == priority_filter)
    if status_filter:
        leads_query = leads_query.filter(Lead.website_status == status_filter)

    leads = leads_query.order_by(Lead.lead_priority_score.desc()).all()

    # Dashboard Statistics (Step 14)
    total_discovered = Lead.query.count()
    no_website_count = Lead.query.filter(Lead.website_status.in_(["No website listed", "Website unavailable or inaccessible"])).count()
    emails_count = Lead.query.filter(Lead.email_address != None, Lead.email_address != "", Lead.email_address != "N/A").count()
    contacted_count = Lead.query.filter(Lead.outreach_status.in_(["Contacted", "Replied", "Interested"])).count()
    won_count = Lead.query.filter(Lead.outreach_status == "Project Won").count()

    stats = {
        "total_discovered": total_discovered,
        "no_website_count": no_website_count,
        "emails_count": emails_count,
        "contacted_count": contacted_count,
        "won_count": won_count
    }

    return render_template("dashboard.html", leads=leads, stats=stats, query_filter=query_filter, priority_filter=priority_filter, status_filter=status_filter)

@app.route("/search", methods=["POST"])
def run_search():
    if db_error_message:
        flash(f"Database Configuration Error: {db_error_message}", "danger")
        return redirect(url_for("dashboard"))

    input_text = request.form.get("search_input", "").strip()
    max_results = int(request.form.get("max_results", 20))

    if not input_text:
        flash("Please enter a Google Maps URL or search phrase.", "warning")
        return redirect(url_for("dashboard"))

    gps = GooglePlacesService()
    search_query = gps.extract_search_query(input_text)

    try:
        raw_listings = gps.fetch_business_listings(search_query, max_results=max_results)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("dashboard"))

    added_count = 0
    updated_count = 0

    for item in raw_listings:
        place_id = item.get("place_id")
        website_url = item.get("website_url")

        # Step 4: Check business website availability and crawl emails
        crawl_res = WebsiteCrawlerService.check_and_extract(website_url)
        website_status = crawl_res["status"]
        found_emails = crawl_res["emails"]
        email_str = ", ".join(found_emails) if found_emails else None

        # Step 5 & 6: Verify website existence if no website listed on Maps
        if website_status == "No website listed":
            verify_res = WebsiteVerifierService.verify_no_website(item["name"], item.get("address", ""))
            verification_status = verify_res["verification_status"]
            research_notes = verify_res["notes"]
        else:
            verification_status = "Verified Listed Website" if crawl_res["accessible"] else "Website Inaccessible Check"
            research_notes = crawl_res.get("error") or "Website accessible"

        # Step 7: Score lead
        lead_data_for_scoring = {
            "website_status": website_status,
            "email_address": email_str,
            "phone_number": item.get("phone"),
            "user_ratings_total": item.get("user_ratings_total"),
            "rating": item.get("rating"),
            "business_category": item.get("category")
        }
        score_res = LeadScorerService.score_lead(lead_data_for_scoring)

        # Step 11: Draft outreach email
        outreach_draft = OutreachGeneratorService.generate_email_draft(
            item["name"],
            item.get("category", ""),
            item.get("address", ""),
            website_status
        )

        existing = Lead.query.filter_by(place_id=place_id).first() if place_id else None
        if existing:
            existing.business_name = item["name"]
            existing.business_category = item.get("category")
            existing.business_address = item.get("address")
            existing.phone_number = item.get("phone")
            existing.website_url = website_url
            existing.website_status = website_status
            existing.website_verification_status = verification_status
            existing.google_maps_url = item.get("google_maps_url")
            existing.lead_priority_score = score_res["lead_priority_score"]
            existing.lead_priority_category = score_res["lead_priority_category"]
            existing.research_notes = research_notes
            if email_str:
                existing.email_address = email_str
                existing.email_research_status = "Found"
            updated_count += 1
        else:
            new_lead = Lead(
                place_id=place_id,
                business_name=item["name"],
                business_category=item.get("category"),
                business_address=item.get("address"),
                phone_number=item.get("phone"),
                email_address=email_str,
                website_url=website_url,
                website_status=website_status,
                website_verification_status=verification_status,
                google_maps_url=item.get("google_maps_url"),
                lead_priority_score=score_res["lead_priority_score"],
                lead_priority_category=score_res["lead_priority_category"],
                email_research_status="Found" if email_str else "Not Found",
                research_notes=research_notes,
                outreach_status="New",
                outreach_email_subject=outreach_draft["subject"],
                outreach_email_body=outreach_draft["body"]
            )
            db.session.add(new_lead)
            added_count += 1

    db.session.commit()
    flash(f"Search successful! Extracted search query: '{search_query}'. Retrieved {len(raw_listings)} leads ({added_count} new, {updated_count} updated).", "success")
    return redirect(url_for("dashboard"))

@app.route("/lead/<int:lead_id>", methods=["GET", "POST"])
def lead_detail(lead_id):
    if db_error_message:
        flash(f"Database Configuration Error: {db_error_message}", "danger")
        return redirect(url_for("dashboard"))

    lead = Lead.query.get_or_404(lead_id)

    if request.method == "POST":
        lead.email_address = request.form.get("email_address", "").strip()
        lead.phone_number = request.form.get("phone_number", "").strip()
        lead.outreach_status = request.form.get("outreach_status", lead.outreach_status)
        lead.follow_up_date = request.form.get("follow_up_date", lead.follow_up_date)
        lead.research_notes = request.form.get("research_notes", lead.research_notes)

        # Regenerate email draft if requested
        if "regenerate_draft" in request.form:
            draft = OutreachGeneratorService.generate_email_draft(
                lead.business_name,
                lead.business_category or "",
                lead.business_address or "",
                lead.website_status or ""
            )
            lead.outreach_email_subject = draft["subject"]
            lead.outreach_email_body = draft["body"]
            flash("Outreach draft regenerated successfully.", "info")

        db.session.commit()
        flash("Lead updated successfully.", "success")
        return redirect(url_for("lead_detail", lead_id=lead.id))

    return render_template("lead_detail.html", lead=lead)

@app.route("/export/csv")
def export_csv():
    if db_error_message:
        return Response(f"Database Error: {db_error_message}", status=500, mimetype="text/plain")

    leads = Lead.query.order_by(Lead.lead_priority_score.desc()).all()
    leads_dicts = [l.to_dict() for l in leads]
    csv_content = ExporterService.export_to_csv(leads_dicts)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=afixtech_business_leads.csv"}
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
