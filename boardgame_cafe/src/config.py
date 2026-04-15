import os
from datetime import timedelta


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    DEBUG = False
    TESTING = False
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # JWT/Auth (if needed)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672/")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "rpc://")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    BOOKING_DRAFT_REDIS_REQUIRED = os.getenv("BOOKING_DRAFT_REDIS_REQUIRED", "false").lower() == "true"

    BOOKING_DRAFT_TTL_SECONDS = int(os.getenv("BOOKING_DRAFT_TTL_SECONDS", str(60 * 60 * 24 * 7)))
    BOOKING_DRAFT_CACHE_DIR = os.getenv("BOOKING_DRAFT_CACHE_DIR")

class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///boardgame_cafe.db"
    )


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    REDIS_URL = None


class ProductionConfig(Config):
    """Production configuration."""
    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/boardgame_cafe"
    )
    DEBUG = False
