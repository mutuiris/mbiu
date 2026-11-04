from django.urls import path

from mbiu import health
from mbiu.api import views

urlpatterns = [
    path("healthz", health.healthz),
    path("readyz", health.readyz),
    path("api/v1/evaluations", views.evaluations),
]
