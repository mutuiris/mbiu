from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import HttpRequest, JsonResponse

from mbiu.corpus.loader import active_snapshot


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. Checks no dependencies."""
    return JsonResponse({"status": "ok"})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: dependencies are usable. Returns 503 listing what failed."""
    # TODO: add the embedding self-test
    failed: list[str] = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        failed.append("database")
    # The first call loads the corpus into memory; later calls reuse it
    if not failed and active_snapshot() is None:
        failed.append("corpus")
    if failed:
        return JsonResponse({"status": "not_ready", "failed": failed}, status=503)
    return JsonResponse({"status": "ready"})
