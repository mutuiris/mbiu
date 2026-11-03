import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_app = get_asgi_application()

from mbiu.observability import TracingMiddleware, setup_tracing  # noqa: E402  For this, the django should be set up first

setup_tracing()
application = TracingMiddleware(django_app)
