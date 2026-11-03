from pathlib import Path
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
    batch_timeout_s: float = Field(default=30, gt=0)


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
INSTALLED_APPS: list[str] = []
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]
DATABASES = {"default": _database(env.database_url)}
USE_TZ = True

OTEL_EXPORTER_OTLP_ENDPOINT = env.otel_exporter_otlp_endpoint
OTEL_EXPORTER_OTLP_HEADERS = env.otel_exporter_otlp_headers
OTEL_SERVICE_NAME = env.otel_service_name

GEMINI_API_KEY = env.gemini_api_key.get_secret_value()
GEMINI_MODEL_MAIN = env.gemini_model_main
GEMINI_MODEL_LIGHT = env.gemini_model_light
BATCH_TIMEOUT_S = env.batch_timeout_s
