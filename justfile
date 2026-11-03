set minimum-version := "1.56.0"

[unix]
set shell := ["sh", "-cu"]

[windows]
set shell := ["powershell.exe", "-NoLogo", "-Command"]

export NEXT_TELEMETRY_DISABLED := "1"

# List all commands
default:
    @just --list

# Start Postgres, PgBouncer, Jaeger and the API (auto-reload), and wait until they are ready
dev:
    docker compose up -d --build --wait

# Install frontend dependencies (the backend installs itself through uv)
install:
    pnpm --dir frontend install

# Start the frontend on http://localhost:3000
web:
    pnpm --dir frontend dev

# Run backend tests
test:
    uv run --directory backend pytest

# Lint and format-check backend and frontend
lint:
    uv run --directory backend ruff check .
    uv run --directory backend ruff format --check .
    pnpm --dir frontend lint

# Type-check backend and frontend
typecheck:
    uv run --directory backend mypy .
    pnpm --dir frontend typecheck

# Stop local services (data is kept)
down:
    docker compose down

# Follow logs, for all services or one: just logs pgbouncer
logs service="":
    docker compose logs -f {{service}}

# Stop local services and delete the local database
reset:
    docker compose down -v
