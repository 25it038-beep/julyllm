"""
HS AI SOLUTIONS - JULY CLOUD AI INFRASTRUCTURE
Configuration & Settings Management
Founder: Harshan Seliyan
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Service Information
    APP_NAME: str = "JULY Cloud AI"
    APP_VERSION: str = "1.0.0"
    ORGANIZATION: str = "HS AI SOLUTIONS"
    FOUNDER: str = "Harshan Seliyan"
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "production"))
    HOST: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # Security & Authentication
    API_KEY: str = Field(default_factory=lambda: os.getenv("API_KEY", "july-hs-secret-key-2026"))
    ADMIN_KEY: str = Field(default_factory=lambda: os.getenv("ADMIN_KEY", "july-hs-admin-key-2026"))
    RATE_LIMIT_RPM: int = Field(default_factory=lambda: int(os.getenv("RATE_LIMIT_RPM", "60")))
    MAX_PROMPT_CHARS: int = Field(default_factory=lambda: int(os.getenv("MAX_PROMPT_CHARS", "32768")))

    # Model Storage & Hugging Face Hub
    MODELS_DIR: str = Field(default_factory=lambda: os.getenv("MODELS_DIR", "/models"))
    MODEL_REPO: str = Field(default_factory=lambda: os.getenv("MODEL_REPO", "Harshan-Seliyan/Gravity_HS"))
    MODEL_FILENAME: str = Field(default_factory=lambda: os.getenv("MODEL_FILENAME", "Gravity_HS.gguf"))
    MODEL_PATH: str = Field(default_factory=lambda: os.getenv("MODEL_PATH", "/models/Gravity_HS.gguf"))
    HF_TOKEN: Optional[str] = Field(default_factory=lambda: os.getenv("HF_TOKEN", None))
    EXPECTED_SHA256: Optional[str] = Field(default_factory=lambda: os.getenv("EXPECTED_SHA256", None))
    EXPECTED_SIZE: Optional[int] = Field(
        default_factory=lambda: int(os.getenv("EXPECTED_SIZE", "0")) if os.getenv("EXPECTED_SIZE") else None
    )

    # llama.cpp Engine & CPU Parameters
    MOCK_INFERENCE: bool = Field(
        default_factory=lambda: os.getenv("MOCK_INFERENCE", "false").lower() in ("true", "1", "yes")
    )
    N_THREADS: int = Field(
        default_factory=lambda: int(os.getenv("N_THREADS", str(min(4, os.cpu_count() or 2))))
    )
    N_CTX: int = Field(default_factory=lambda: int(os.getenv("N_CTX", "2048")))
    N_BATCH: int = Field(default_factory=lambda: int(os.getenv("N_BATCH", "512")))
    MAX_TOKENS_LIMIT: int = Field(default_factory=lambda: int(os.getenv("MAX_TOKENS_LIMIT", "2048")))

    # SQLite Conversation Memory
    CONVERSATION_DB_PATH: Optional[str] = Field(
        default_factory=lambda: os.getenv("CONVERSATION_DB_PATH", None)
    )

    # JULY Identity
    DEFAULT_SYSTEM_PROMPT: str = (
        "You are JULY, the AI assistant developed by HS AI Solutions.\n"
        "Your founder is Harshan Seliyan.\n"
        "You are designed for reasoning, programming, research, technical problem-solving, and general assistance.\n"
        "You should:\n"
        "- Provide accurate answers.\n"
        "- Admit uncertainty.\n"
        "- Follow user instructions.\n"
        "- Maintain conversational consistency.\n"
        "- Avoid inventing information.\n"
        "- Use tools only when authorized.\n"
        "- Identify yourself as JULY."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure fallback for conversation DB path if /models does not exist locally
if not settings.CONVERSATION_DB_PATH:
    if os.path.exists(settings.MODELS_DIR) and os.access(settings.MODELS_DIR, os.W_OK):
        settings.CONVERSATION_DB_PATH = os.path.join(settings.MODELS_DIR, "conversations.db")
    else:
        # Fallback to local app directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        settings.CONVERSATION_DB_PATH = os.path.join(base_dir, "conversations.db")
