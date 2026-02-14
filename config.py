"""
Configuration module for PATMASTER Document Extraction Pipeline
Loads environment variables and provides configuration settings
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    llama_cloud_api_key: str
    gemini_api_key: str

    # Database Configuration (Turso SQLite) — MUST be set via env
    turso_database_url: str
    turso_auth_token: str

    # JWT Authentication (MUST be set via env — no default)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Cloudinary Cloud Storage (NO local disk storage)
    # These will be loaded from environment variables in production
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Concurrency Settings
    max_concurrent_extractions: int = 50

    # Timeouts (seconds)
    extraction_timeout: int = 300
    diagram_description_timeout: int = 60

    # Environment
    environment: str = "development"

    # Project Paths
    base_dir: Path = Path(__file__).parent
    extracted_output_dir: Path = base_dir / "extracted_output"
    static_dir: Path = base_dir / "static"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.extracted_output_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)


# Initialize settings
try:
    settings = Settings()
    logger.info(f"Settings loaded successfully from {settings.base_dir / '.env'}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Max concurrent extractions: {settings.max_concurrent_extractions}")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    logger.warning("Make sure you have created a .env file with required API keys")
    logger.warning("Copy .env.example to .env and fill in your API keys")
    raise


def get_session_output_dir(user_id: str, session_id: str) -> Path:
    """Get or create output directory for a specific user session"""
    session_dir = settings.extracted_output_dir / f"{user_id}_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def validate_api_keys():
    """Validate that API keys are set and not placeholder values"""
    if "xxx" in settings.llama_cloud_api_key.lower():
        raise ValueError("LLAMA_CLOUD_API_KEY is not set. Please update your .env file")

    if "xxx" in settings.gemini_api_key.lower():
        raise ValueError("GEMINI_API_KEY is not set. Please update your .env file")

    logger.success("API keys validated successfully")
    return True
