"""Tests create, change and delete data, so they must never reach a shared database."""

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1", "postgres", "pgbouncer"}


def is_local_database_host(host: str | None) -> bool:
    """True for this machine and the docker compose services; False for anything remote."""
    return (host or "") in LOCAL_HOSTS
