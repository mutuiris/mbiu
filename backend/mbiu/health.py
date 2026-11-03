from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import HttpRequest, JsonResponse

from mbiu.corpus.loader import get_active_corpus_snapshot


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. Checks no dependencies."""
    return JsonResponse({"status": "ok"})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: dependencies are usable. Returns 503 listing what failed."""
    failed: list[str] = []

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        failed.append("database")

    snapshot = get_active_corpus_snapshot()
    if snapshot is None:
        failed.append("corpus")

    if failed:
        return JsonResponse({"status": "not_ready", "failed": failed}, status=503)

    return JsonResponse({"status": "ready"})
