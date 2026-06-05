import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory of the backend folder and resolve root .env path
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    ZOHO_CLIENT_ID: str = Field(default="")
    ZOHO_CLIENT_SECRET: str = Field(default="")
    ZOHO_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/callback")
    ZOHO_ACCOUNTS_URL: str = Field(default="https://accounts.zoho.com")
    ZOHO_API_BASE: str = Field(default="https://projectsapi.zoho.com/restapi")
    ANTHROPIC_API_KEY: str = Field(default="")
    SECRET_KEY: str = Field(default="your-random-secret-for-sessions")
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./zoho_chatbot.db")
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
