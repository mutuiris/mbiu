from tests.database_guard import is_local_database_host


def test_local_and_compose_hosts_are_allowed() -> None:
    for host in ["localhost", "127.0.0.1", "::1", "postgres", "pgbouncer", None, ""]:
        assert is_local_database_host(host), host


def test_remote_databases_are_refused() -> None:
    for host in [
        "aws-0-eu-central-1.pooler.supabase.com",
        "db.qdfpncpxmzjnegrmthws.supabase.co",
        "10.0.0.5",
    ]:
        assert not is_local_database_host(host), host
