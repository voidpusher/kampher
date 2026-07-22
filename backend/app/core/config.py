"""Application configuration.

Twelve-factor: every knob is an environment variable prefixed with ``KAMPHER_``
(except provider API keys, which follow their SDK conventions). A single
``Settings`` instance is created lazily and shared process-wide.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KAMPHER_",
        # Support running from the repo root (Docker) or from backend/ (local dev);
        # entries later in the tuple win.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    env: Environment = Environment.DEV
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Storage
    database_url: str = "postgresql+asyncpg://kampher:kampher@localhost:5432/kampher"
    database_url_sync: str = "postgresql+psycopg://kampher:kampher@localhost:5432/kampher"
    redis_url: str = "redis://localhost:6379/0"
    redis_health_check: bool = False
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    # Set to a directory path to run Qdrant embedded (no server, no Docker).
    # Caveat: embedded mode is single-process — fine for run_once dev flows,
    # not for API + workers concurrently.
    qdrant_path: str | None = None

    # AI
    llm_provider: str = "anthropic"  # anthropic | gemini
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    llm_model: str = "claude-sonnet-5"
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    embedding_provider: str = "fastembed"  # fastembed | local (torch)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    pipeline_version: int = 1
    target_languages: list[str] = Field(default_factory=lambda: ["en"])

    # Sources
    reddit_client_id: str = ""
    reddit_client_secret: SecretStr | None = None
    reddit_user_agent: str = "kampher/0.1"
    reddit_subreddits: list[str] = Field(default_factory=lambda: ["SaaS", "startups"])

    x_bearer_token: SecretStr | None = None
    x_queries: list[str] = Field(default_factory=list)

    github_token: SecretStr | None = None
    github_repos: list[str] = Field(default_factory=list)

    hn_enabled: bool = True

    stackoverflow_enabled: bool = True
    # Tags rich in unmet-need language; anonymous API quota is 300 req/day
    # (one request per tag per sweep, so this list costs 15/day per sweep).
    stackoverflow_tags: list[str] = Field(
        default_factory=lambda: [
            "authentication",
            "payments",
            "deployment",
            "web-scraping",
            "saas",
            "stripe-payments",
            "oauth-2.0",
            "docker",
            "aws",
            "firebase",
            "next.js",
            "fastapi",
            "webhooks",
            "google-api",
            "cron",
        ]
    )
    stackoverflow_key: str = ""  # optional app key raises quota to 10k/day

    lobsters_enabled: bool = True

    devto_enabled: bool = True
    devto_tags: list[str] = Field(
        default_factory=lambda: ["devops", "webdev", "productivity", "startup", "career"]
    )

    @property
    def is_dev(self) -> bool:
        return self.env is Environment.DEV


@lru_cache
def get_settings() -> Settings:
    return Settings()
