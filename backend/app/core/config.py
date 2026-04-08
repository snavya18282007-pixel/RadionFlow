from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


_BASE_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = (str(_BASE_DIR / ".env"), str(_BASE_DIR / ".venv"))


def normalize_database_url(raw_url: str) -> str:
    value = raw_url.strip()
    if value.startswith("postgres://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgres://")
    elif value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgresql://")
    elif value.startswith("postgresql+psycopg://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgresql+psycopg://")
    elif value.startswith("postgresql+psycopg2://"):
        value = "postgresql+asyncpg://" + value.removeprefix("postgresql+psycopg2://")

    parsed = urlsplit(value)
    if parsed.scheme != "postgresql+asyncpg":
        return value

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    host = (parsed.hostname or "").lower()
    if "supabase.co" in host and "ssl" not in query and "sslmode" not in query:
        query["ssl"] = "require"
        value = urlunsplit(parsed._replace(query=urlencode(query)))

    return value


def redact_database_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if not parsed.netloc:
        return raw_url

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if parsed.username:
        netloc = f"{parsed.username}:***@{hostname}{port}"
    else:
        netloc = f"{hostname}{port}"
    return urlunsplit(parsed._replace(netloc=netloc))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Radiology Triage & Decision Support Platform"
    environment: str = "dev"
    log_level: str = "INFO"

    # Local runtime defaults to SQLite; PostgreSQL remains supported via DATABASE_URL.
    database_url: str = "sqlite+aiosqlite:///./medicathon.db"
    database_fallback_url: str = "sqlite+aiosqlite:///./medicathon.db"
    database_allow_fallback: bool = True
    supabase_url: str | None = None
    supabase_key: str | None = None
    admin_access_code: str | None = None
    jwt_secret_key: str = "change-me-before-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Model settings
    hf_model_name: str = "distilbert-base-uncased"
    hf_zero_shot_model: str = "facebook/bart-large-mnli"
    hf_device: str = "cpu"  # "cpu" or "cuda"

    # Feature toggles
    enable_explainability: bool = True
    enable_inconsistency_checks: bool = True

    # Frontend / automation integration
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    n8n_webhook_url: str | None = None

    @property
    def resolved_database_url(self) -> str:
        return normalize_database_url(self.database_url)

    @property
    def redacted_database_url(self) -> str:
        return redact_database_url(self.resolved_database_url)

    @property
    def resolved_database_fallback_url(self) -> str:
        return normalize_database_url(self.database_fallback_url)


class AppMeta(BaseModel):
    name: str
    environment: str
    version: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
