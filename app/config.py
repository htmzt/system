# app/config.py
"""
Application Configuration
Loads settings from environment variables (.env file)
"""

from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    Pydantic automatically reads from .env file
    """
    
    # ========== APPLICATION INFO ==========
    APP_NAME: str = "Internal PO System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, production, testing
    
    # ========== DATABASE ==========
    DATABASE_URL: str  # Will be loaded from .env
    # No default value - MUST be set in .env
    
    # ========== JWT CONFIGURATION ==========
    SECRET_KEY: str  # Will be loaded from .env
    # No default value - MUST be set in .env
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ========== SECURITY SETTINGS ==========
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    # Password requirements
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGIT: bool = True
    REQUIRE_SPECIAL_CHAR: bool = False
    
    # ========== CORS SETTINGS ==========
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # ========== EMAIL CONFIGURATION ==========
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "sib.service.it@gmail.com"
    SMTP_PASSWORD: str = "yjjn gylw agtu romb"
    SMTP_FROM_EMAIL: str = "sib.service.it@gmail.com"
    SMTP_FROM_NAME: str = "Internal PO System"
    
    # Frontend URL (for email verification/reset links)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # ========== FIRST ADMIN ACCOUNT ==========
    FIRST_ADMIN_EMAIL: str = "admin@sib.com"
    FIRST_ADMIN_PASSWORD: str = "Admin123!"
    FIRST_ADMIN_NAME: str = "System Administrator"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'  # Ignore extra fields in .env


# Create global settings instance
settings = Settings()


# Print loaded config (for debugging)
if __name__ == "__main__":
    print("=" * 60)
    print("CONFIGURATION LOADED")
    print("=" * 60)
    print(f"App Name: {settings.APP_NAME}")
    print(f"Version: {settings.APP_VERSION}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Secret Key: {'*' * 20} (hidden)")
    print(f"Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print("=" * 60)