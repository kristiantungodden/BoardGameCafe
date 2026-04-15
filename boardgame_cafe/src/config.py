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

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    REALTIME_EVENTS_CHANNEL = os.getenv("REALTIME_EVENTS_CHANNEL", "boardgame_cafe.events")

    # Email (Flask-Mail / SMTP)
    # Support both MAIL_* and legacy SMTP_* variable names.
    MAIL_SERVER = os.getenv("MAIL_SERVER", os.getenv("SMTP_SERVER", "localhost"))
    MAIL_PORT = int(os.getenv("MAIL_PORT", os.getenv("SMTP_PORT", "587")))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() in {"1", "true", "yes", "on"}
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", os.getenv("SMTP_USER"))
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", os.getenv("SMTP_PASSWORD"))
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "no-reply@localhost")
    MAIL_SUPPRESS_SEND = os.getenv("MAIL_SUPPRESS_SEND", "false").lower() in {"1", "true", "yes", "on"}

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
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    """Production configuration."""
    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/boardgame_cafe"
    )
    DEBUG = False
