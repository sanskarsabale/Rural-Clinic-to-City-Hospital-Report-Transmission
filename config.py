import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base Configuration for RuralLink"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rurallink-dc-secret-key-2026-academic-btech')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'rurallink-jwt-encryption-key-789012')
    JWT_EXPIRATION_DELTA = timedelta(hours=8)
    
    # Database Configuration: SQLite for local dev, PostgreSQL for production
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        # Fix for SQLAlchemy 1.4+ / 2.0 where postgres:// is deprecated in favor of postgresql://
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = db_url or f"sqlite:///{os.path.join(BASE_DIR, 'rurallink.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB maximum file size
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Data Communication Academic Settings
    ENABLE_NETWORK_SIMULATION = True  # Allows simulating latency and packet drops
    ACK_TIMEOUT_SECONDS = 10
    MAX_RETRY_ATTEMPTS = 5
    
    # CORS & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
    SESSION_COOKIE_SECURE = True

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
