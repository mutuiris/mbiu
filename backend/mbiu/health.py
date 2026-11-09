from django.conf import settings
from django.db import connection
from django.db.utils import Error as DatabaseError
from django.http import HttpRequest, JsonResponse

from mbiu.corpus.loader import active_snapshot


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
    # The first call loads the corpus into memory; later calls reuse it
    snapshot = None if failed else active_snapshot()
    if not failed and snapshot is None:
        failed.append("corpus")
    # Corpus vectors only compare with clause vectors from the same model
    if snapshot is not None and snapshot.embedding_model_id != settings.EMBEDDING_MODEL_ID:
        failed.append("embeddings")
    if failed:
        return JsonResponse({"status": "not_ready", "failed": failed}, status=503)
    return JsonResponse({"status": "ready"})
