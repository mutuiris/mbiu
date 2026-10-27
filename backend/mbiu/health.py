from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import HttpRequest, JsonResponse


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up. Checks no dependencies."""
    return JsonResponse({"status": "ok"})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: dependencies are usable. Returns 503 listing what failed."""
    # TODO: add the embedding self-test and the corpus snapshot check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "not_ready", "failed": ["database"]}, status=503)
    return JsonResponse({"status": "ready"})
