"""
WSGI entry point for production deployment (Render, Railway, etc.)
Run with: gunicorn wsgi:app
"""
from app import create_app
from models import db, User

app = create_app('production')

# Auto-create tables and seed on first deploy
with app.app_context():
    db.create_all()
    if not User.query.first():
        try:
            from seed_data import seed_database
            seed_database()
        except Exception as e:
            print(f"Seeding skipped: {e}")
