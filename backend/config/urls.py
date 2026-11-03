from django.urls import path

from mbiu import health

urlpatterns = [
    path("healthz", health.healthz),
    path("readyz", health.readyz),
]
