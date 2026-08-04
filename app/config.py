"""
Configuration module for KrickBot.

Loads environment variables from .env file and exposes them as typed config values.
All configuration is centralized here so no other module reads env vars directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from app/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # --- Main Database (MariaDB for Stats) ---
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "krickbot")

    # --- Chat Database (PostgreSQL for History) ---
    CHAT_DB_HOST: str = os.getenv("CHAT_DB_HOST", "localhost")
    CHAT_DB_PORT: int = int(os.getenv("CHAT_DB_PORT", "5432"))
    CHAT_DB_USER: str = os.getenv("CHAT_DB_USER", "postgres")
    CHAT_DB_PASSWORD: str = os.getenv("CHAT_DB_PASSWORD", "postgres")
    CHAT_DB_NAME: str = os.getenv("CHAT_DB_NAME", "krickbot_chats")

    # --- Server ---
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "GROQ")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def DATABASE_URL(self) -> str:
        """
        SQLAlchemy connection string for MariaDB via PyMySQL.

        Format: mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4
        We use utf8mb4 charset to support full Unicode (including Urdu text in the DB).
        """
        password_part = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return (
            f"mysql+pymysql://{self.DB_USER}{password_part}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def CHAT_DATABASE_URL(self) -> str:
        """
        SQLAlchemy connection string for Chat History.
        Defaults to MariaDB so a separate PostgreSQL setup is not required.
        """
        if os.getenv("USE_POSTGRES_CHAT_DB") == "true":
            password_part = f":{self.CHAT_DB_PASSWORD}" if self.CHAT_DB_PASSWORD else ""
            return (
                f"postgresql://{self.CHAT_DB_USER}{password_part}"
                f"@{self.CHAT_DB_HOST}:{self.CHAT_DB_PORT}/{self.CHAT_DB_NAME}"
            )
        return self.DATABASE_URL


# Singleton instance — import this everywhere
settings = Settings()
