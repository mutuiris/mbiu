from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Env(BaseSettings):
    """Typed environment settings.

    Read from environment variables, then from the repo's .env file in local development.
    A missing required value stops the app at startup.
    """

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    django_secret_key: str = Field(min_length=50)
    django_allowed_hosts: str = Field(min_length=1)
    database_url: str = Field(min_length=1)
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    otel_service_name: str = "mbiu-api"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model_main: str = "gemini-3.8-flash"
    gemini_model_light: str = "gemini-3.5-flash-lite"
    # Hidden reasoning before answering: more is slower and costs output tokens
    gemini_thinking_level: Literal["minimal", "low", "medium", "high"] = "low"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    embedding_model_id: str = "gemini-embedding-2"
    failover_enabled: bool = False
    active_corpus_version: str = "synthetic-v0"
    batch_timeout_s: float = Field(default=30, gt=0)
    batch_size: int = Field(default=6, gt=0)
    llm_concurrency: int = Field(default=4, gt=0)
    token_budget_per_contract: int = Field(default=400_000, gt=0)
    deadline_per_clause_s: float = Field(default=3.0, gt=0)
    deadline_cap_s: float = Field(default=300.0, gt=0)
    max_reading_grade: float = Field(default=9.0, gt=0)
    cors_allowed_origins: str = "http://localhost:3000"
    max_upload_mb: int = 10
    max_pages: int = 40
    # Slow, shared CPUs (free hosting) need more time just to start the extraction worker
    extraction_timeout_s: float = Field(default=30.0, gt=0)
    extraction_timeout_per_page_s: float = Field(default=0.5, ge=0)
    # Required: a default here would be a bot check that always passes
    turnstile_secret_key: str = Field(min_length=1)
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


env = Env()  # pyright: ignore[reportCallIssue]  The values come from the environment


def _database(url: str) -> dict[str, object]:
    parts = urlsplit(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parts.path.lstrip("/"),
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": parts.hostname,
        "PORT": parts.port or 5432,
        # Required by transaction-mode poolers (PgBouncer, Supavisor). Don't change this
        "CONN_MAX_AGE": 0,
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "OPTIONS": {"prepare_threshold": None},
    }


SECRET_KEY = env.django_secret_key
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in env.django_allowed_hosts.split(",") if h.strip()]
ROOT_URLCONF = "config.urls"
INSTALLED_APPS = ["mbiu.corpus"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]
DATABASES = {"default": _database(env.database_url)}
USE_TZ = True

OTEL_EXPORTER_OTLP_ENDPOINT = env.otel_exporter_otlp_endpoint
OTEL_EXPORTER_OTLP_HEADERS = env.otel_exporter_otlp_headers
OTEL_SERVICE_NAME = env.otel_service_name

GEMINI_API_KEY = env.gemini_api_key.get_secret_value()
GEMINI_MODEL_MAIN = env.gemini_model_main
GEMINI_MODEL_LIGHT = env.gemini_model_light
GEMINI_THINKING_LEVEL = env.gemini_thinking_level
OPENAI_API_KEY = env.openai_api_key.get_secret_value()
OPENAI_MODEL = env.openai_model
EMBEDDING_MODEL_ID = env.embedding_model_id
FAILOVER_ENABLED = env.failover_enabled
ACTIVE_CORPUS_VERSION = env.active_corpus_version
TOKEN_BUDGET_PER_CONTRACT = env.token_budget_per_contract
BATCH_TIMEOUT_S = env.batch_timeout_s
BATCH_SIZE = env.batch_size
LLM_CONCURRENCY = env.llm_concurrency
TOKEN_BUDGET_PER_CONTRACT = env.token_budget_per_contract
DEADLINE_PER_CLAUSE_S = env.deadline_per_clause_s
DEADLINE_CAP_S = env.deadline_cap_s
MAX_READING_GRADE = env.max_reading_grade
CORS_ALLOWED_ORIGINS = [o.strip() for o in env.cors_allowed_origins.split(",") if o.strip()]
MAX_UPLOAD_MB = env.max_upload_mb
MAX_PAGES = env.max_pages
EXTRACTION_TIMEOUT_S = env.extraction_timeout_s
EXTRACTION_TIMEOUT_PER_PAGE_S = env.extraction_timeout_per_page_s
TURNSTILE_SECRET_KEY = env.turnstile_secret_key
TURNSTILE_VERIFY_URL = env.turnstile_verify_url
