import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_database_uri():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or db_url.startswith("sqlite"):
        # Explicit error per user directive: No SQLite fallback
        raise ValueError("Connect Supabase (DATABASE_URL environment variable is required to connect to Supabase PostgreSQL database)")

    # Handle SQLAlchemy 1.4+ postgres:// -> postgresql:// conversion if needed
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    return db_url
