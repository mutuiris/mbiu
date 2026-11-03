from pathlib import Path
from urllib.parse import unquote, urlsplit

from pydantic import Field
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
    database_direct_url: str = ""
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    otel_service_name: str = "mbiu-api"
    max_upload_mb: int = 10
    max_pages: int = 40
    turnstile_secret_key: str = "1x0000000000000000000000000000000AA"
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


env = Env()  # pyright: ignore[reportCallIssue]  The values come from the environment


def _database(url: str) -> dict[str, object]:
    parts = urlsplit(url)
    if parts.scheme in ("sqlite", "sqlite3"):
        name = parts.path.lstrip("/") if parts.path.startswith("/:") else (parts.path or ":memory:")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }
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
        "OPTIONS": {
            "prepare_threshold": None,
            "connect_timeout": 3,
        },
    }


SECRET_KEY = env.django_secret_key
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in env.django_allowed_hosts.split(",") if h.strip()]
ROOT_URLCONF = "config.urls"
INSTALLED_APPS: list[str] = [
    "pgvector.django",
    "mbiu.corpus",
]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]
DATABASES: dict[str, dict[str, object]] = {"default": _database(env.database_url)}
if env.database_direct_url:
    DATABASES["direct"] = _database(env.database_direct_url)
USE_TZ = True

OTEL_EXPORTER_OTLP_ENDPOINT = env.otel_exporter_otlp_endpoint
OTEL_EXPORTER_OTLP_HEADERS = env.otel_exporter_otlp_headers
OTEL_SERVICE_NAME = env.otel_service_name

MAX_UPLOAD_MB = env.max_upload_mb
MAX_PAGES = env.max_pages
TURNSTILE_SECRET_KEY = env.turnstile_secret_key
TURNSTILE_VERIFY_URL = env.turnstile_verify_url
