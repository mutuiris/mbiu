from django.urls import path

from mbiu import health
from mbiu.evaluation.views import clause_evaluations_view

urlpatterns = [
    path("healthz", health.healthz),
    path("readyz", health.readyz),
    path("api/v1/clause-evaluations", clause_evaluations_view),
    path("api/v1/clause-evaluations/", clause_evaluations_view),
]
