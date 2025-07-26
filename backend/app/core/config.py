from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import urllib.parse

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dad's Invoice Pro API"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SERVER_HOST: str = "http://localhost:8000"

    # Database
    POSTGRES_SERVER: Optional[str] = "localhost"
    POSTGRES_USER: Optional[str] = "invoice_user"
    POSTGRES_PASSWORD: Optional[str] = "securepassword123" # Default, should be overridden by .env
    POSTGRES_DB: Optional[str] = "dads_invoice_db"
    POSTGRES_PORT: int = 5435
    DATABASE_URL: Optional[str] = None # Will be constructed

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None

    # Deepgram
    DEEPGRAM_API_KEY: Optional[str] = None

    # WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    RECIPIENT_WHATSAPP_NUMBER: Optional[str] = None

    # --- NEW SECURITY SETTINGS ---
    SECRET_KEY: str = "a_very_secret_key_that_should_be_strong_and_from_env" # CHANGE THIS IN .ENV
    # Algorithm for signing JWTs (HS256 is common)
    ALGORITHM: str = "HS256"
    # Access token expiration time in minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days for convenience, adjust as needed
    # --- END NEW SECURITY SETTINGS ---

    # --- NEW: Gemini Settings ---
    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-preview-05-20" # Or your preferred model
    # --- END NEW: Gemini Settings ---

    model_config = SettingsConfigDict(
        # Corrected path: four .parent calls to get to project root
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True
    )

settings = Settings()

# Construct DATABASE_URL after settings are loaded
if settings.POSTGRES_USER and settings.POSTGRES_PASSWORD and \
   settings.POSTGRES_SERVER and settings.POSTGRES_DB and settings.POSTGRES_PORT:
    # URL-encode the password
    encoded_password = urllib.parse.quote_plus(settings.POSTGRES_PASSWORD) # <--- USE ENCODED PASSWORD
    settings.DATABASE_URL = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{encoded_password}@" # <--- USE ENCODED PASSWORD
        f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
else:
    print("Database URL could not be constructed. Check POSTGRES environment variables in .env and config defaults.")


# --- NEW: Validate Gemini API Key ---
if not settings.GOOGLE_GEMINI_API_KEY:
    print("WARNING: GOOGLE_GEMINI_API_KEY is not set. AI features will not work.")


