from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "BREW & BEAN — Landing & Bean AI API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "DEBUG"

    DATABASE_URL: str = "postgresql+asyncpg://cafe_owner:password@localhost:5432/cafe_db"
    MIGRATION_DATABASE_URL: str = "postgresql+asyncpg://cafe_owner:password@localhost:5432/cafe_db"

    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:4173",
    ]
    CORS_ORIGIN_REGEX: str | None = None

    SESSION_TOKEN_PEPPER: str = "change-this-secret-pepper"

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    CF_ACCESS_CLIENT_ID: str = ""
    CF_ACCESS_CLIENT_SECRET: str = ""

    LLM_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    OLLAMA_CONNECT_TIMEOUT_S: float = 4.0
    OLLAMA_READ_TIMEOUT_S: float = 75.0
    LLM_MAX_CONCURRENCY: int = 1
    LLM_QUEUE_TIMEOUT_S: float = 20.0
    LLM_NUM_CTX: int = 4096
    LLM_NUM_PREDICT: int = 650
    LLM_THINK_NUM_PREDICT: int = 2048
    LLM_TEMPERATURE: float = 0.3

    RAG_TOP_K_DENSE: int = 20
    RAG_TOP_K_LEXICAL: int = 20
    RAG_RRF_K: int = 60
    RAG_FINAL_TOP_K: int = 4
    RAG_HISTORY_TURNS: int = 4
    RAG_MIN_RELEVANCE: float = 0.35

    SESSION_TTL_HOURS: int = 24
    CHAT_MAX_MESSAGE_LENGTH: int = 1000
    CHAT_RATE_LIMIT_PER_MIN: int = 8
    AUTO_SEED_ANSWER_CACHE: bool = True
    ANSWER_CACHE_SEED_PATH: str = ""
    ANSWER_CACHE_TTL_DAYS: int = 7

    @field_validator("DATABASE_URL", "MIGRATION_DATABASE_URL", mode="before")
    @classmethod
    def normalize_asyncpg_url(cls, value: str) -> str:
        """Convert Neon libpq-style URLs (?sslmode=require&channel_binding=...) for asyncpg."""
        if not isinstance(value, str):
            return value
        raw = value.strip()
        if not raw:
            return raw

        parsed = urlsplit(raw)
        scheme = (
            "postgresql+asyncpg"
            if parsed.scheme in ("postgres", "postgresql")
            else parsed.scheme
        )

        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        has_ssl = any(k == "ssl" for k, _ in query_items)
        if not has_ssl:
            sslmode_val = next((v.lower() for k, v in query_items if k == "sslmode"), None)
            if sslmode_val and sslmode_val != "disable":
                query_items.append(("ssl", "require"))

        filtered_items = [
            (k, v) for k, v in query_items if k not in {"sslmode", "channel_binding"}
        ]
        new_query = urlencode(filtered_items)
        return urlunsplit((scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
