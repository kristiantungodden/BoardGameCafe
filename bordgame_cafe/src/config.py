"""
Application configuration.

Loads settings from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "Board Game Café"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./boardgame_cafe.db"
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Email (optional)
    smtp_server: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    
    # Vipps Payment
    vipps_api_key: str = ""
    vipps_merchant_id: str = ""
    vipps_api_url: str = "https://api.vipps.no"
    vipps_callback_url: str = "http://localhost:8000/payment/callback"
    
    class Config:
        env_file = ".env"


settings = Settings()
