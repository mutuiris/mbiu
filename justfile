set minimum-version := "1.56.0"

[unix]
set shell := ["sh", "-cu"]

[windows]
set shell := ["powershell.exe", "-NoLogo", "-Command"]

# List all commands
default:
    @just --list

# Start Postgres, PgBouncer, Jaeger and the API (auto-reload), and wait until they are ready
dev:
    docker compose up -d --build --wait

# Run backend tests
test:
    uv run --directory backend pytest

# Lint and format-check the backend
lint:
    uv run --directory backend ruff check .
    uv run --directory backend ruff format --check .

# Type-check the backend
typecheck:
    uv run --directory backend mypy .

# Stop local services (data is kept)
down:
    docker compose down

# Follow logs, for all services or one: just logs pgbouncer
logs service="":
    docker compose logs -f {{service}}

# Stop local services and delete the local database
reset:
    docker compose down -v
