"""Application Configuration using Pydantic Settings."""

import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "AI Financial Scam Conversation Detector"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Auth
    SECRET_KEY: str = "temporary-super-secret-key-change-in-production-use-at-least-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./scam_detector.db"

    # LLM Settings
    LLM_PROVIDER: str = "rule_based"  # options: "openai", "gemini", "anthropic", "groq", "rule_based"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 15
    LLM_FALLBACK_TO_RULE_BASED: bool = True

    # OCR Settings
    TESSERACT_CMD: str = ""
    OCR_CONFIDENCE_THRESHOLD: float = 50.0

    # File Upload Limits & Safety
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: Union[List[str], str] = ["jpg", "jpeg", "png", "webp", "bmp"]
    ALLOWED_IMAGE_MIME_TYPES: Union[List[str], str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
    ]

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Safety limits
    ALLOW_GUEST_SCANS: bool = True
    MAX_TEXT_LENGTH_CHARS: int = 20000

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return []

    @field_validator("ALLOWED_IMAGE_EXTENSIONS", "ALLOWED_IMAGE_MIME_TYPES", mode="before")
    @classmethod
    def assemble_list(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return []

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
