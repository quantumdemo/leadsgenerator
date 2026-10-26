from datetime import datetime
from database import db

class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(255), unique=True, nullable=True)
    business_name = db.Column(db.String(255), nullable=False)
    business_category = db.Column(db.String(255), nullable=True)
    business_address = db.Column(db.Text, nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    email_address = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.Text, nullable=True)
    website_status = db.Column(db.String(100), nullable=True)
    website_verification_status = db.Column(db.String(100), nullable=True)
    google_maps_url = db.Column(db.Text, nullable=True)
    lead_priority_score = db.Column(db.Integer, default=0)
    lead_priority_category = db.Column(db.String(50), default='Low')
    email_research_status = db.Column(db.String(100), default='Pending')
    research_notes = db.Column(db.Text, nullable=True)
    outreach_status = db.Column(db.String(100), default='New')
    follow_up_date = db.Column(db.String(50), nullable=True)
    outreach_email_subject = db.Column(db.Text, nullable=True)
    outreach_email_body = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "place_id": self.place_id,
            "business_name": self.business_name,
            "business_category": self.business_category,
            "business_address": self.business_address,
            "phone_number": self.phone_number,
            "email_address": self.email_address,
            "website_url": self.website_url,
            "website_status": self.website_status,
            "website_verification_status": self.website_verification_status,
            "google_maps_url": self.google_maps_url,
            "lead_priority_score": self.lead_priority_score,
            "lead_priority_category": self.lead_priority_category,
            "email_research_status": self.email_research_status,
            "research_notes": self.research_notes,
            "outreach_status": self.outreach_status,
            "follow_up_date": self.follow_up_date,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
