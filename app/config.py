from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Gemini API settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"

    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Application settings
    MAX_CONVERSATION_LENGTH: int = 50  # Maximum messages per conversation
    MAX_TOKENS: int = 8192
    TEMPERATURE: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
