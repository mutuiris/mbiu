"""App configuration for mbiu.corpus."""

import sys

from django.apps import AppConfig


class CorpusConfig(AppConfig):
    """Corpus app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mbiu.corpus"

    def ready(self) -> None:
        """Attempt to load the active corpus snapshot into memory at startup."""
        skip_commands = {
            "makemigrations",
            "migrate",
            "collectstatic",
            "check",
            "shell",
            "pytest",
            "mypy",
        }
        if any(cmd in sys.argv[0] or any(cmd in arg for arg in sys.argv) for cmd in skip_commands):
            return

        from mbiu.corpus.loader import load_corpus_snapshot

        try:
            load_corpus_snapshot()
        except Exception:
            # During startup before migrations, loading is non-blocking.
            pass
