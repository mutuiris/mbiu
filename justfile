set minimum-version := "1.56.0"

[unix]
set shell := ["sh", "-cu"]

[windows]
set shell := ["powershell.exe", "-NoLogo", "-Command"]

# List all commands
default:
    @just --list

# Start Postgres, PgBouncer and Jaeger, and wait until they are ready
dev:
    docker compose up -d --wait

# Stop local services (data is kept)
down:
    docker compose down

# Follow logs, for all services or one: just logs pgbouncer
logs service="":
    docker compose logs -f {{service}}

# Stop local services and delete the local database
reset:
    docker compose down -v
