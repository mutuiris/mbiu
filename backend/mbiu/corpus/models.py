"""The only four application tables.

They hold public reference material and its provenance. There is no table for artists'
contracts or their results, and there must never be one.
"""

import uuid

from django.db import models, transaction
from pgvector.django import VectorField

EMBEDDING_DIM = 768


class ReferenceSource(models.Model):
    """One public document a template, statute or guidance text came from."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=2048)
    document_sha256 = models.CharField(max_length=64, help_text="SHA-256 of the stored original")
    licence = models.CharField(max_length=100)
    reviewing_body = models.CharField(max_length=255)
    template_version = models.CharField(max_length=50)
    contract_type = models.CharField(max_length=50)
    jurisdiction = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reference_sources"

    def __str__(self) -> str:
        """Title and jurisdiction."""
        return f"{self.title} ({self.jurisdiction})"


class CorpusVersion(models.Model):
    """A published corpus. Never edited in place: changes publish a new version."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version_tag = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)
    embedding_model_id = models.CharField(max_length=255)
    embedding_revision = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "corpus_versions"
        constraints = [
            # The single active-version pointer, enforced by the database
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="one_active_corpus_version",
            ),
        ]

    def __str__(self) -> str:
        """Version tag, marked when active."""
        return f"{self.version_tag}{' (active)' if self.is_active else ''}"

    @classmethod
    def activate(cls, version_tag: str) -> CorpusVersion:
        """Point the API at this version in one transaction, so a rollback is one call."""
        with transaction.atomic():
            target = cls.objects.select_for_update().get(version_tag=version_tag)
            cls.objects.filter(is_active=True).exclude(pk=target.pk).update(is_active=False)
            cls.objects.filter(pk=target.pk).update(is_active=True)
        target.is_active = True
        return target


class ReferenceChunk(models.Model):
    """One clause or section of a reference source, embedded for retrieval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corpus_version = models.ForeignKey(
        CorpusVersion, on_delete=models.CASCADE, related_name="chunks"
    )
    # PROTECT: a chunk must always be traceable to where it came from
    source = models.ForeignKey(ReferenceSource, on_delete=models.PROTECT, related_name="chunks")
    chunk_key = models.CharField(max_length=100, help_text="Readable ID, e.g. KE-RECORDING-01")
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    topic = models.CharField(max_length=50)
    contract_type = models.CharField(max_length=50)
    jurisdiction = models.CharField(max_length=50)
    drafted_for = models.CharField(max_length=20, help_text="label, artist or neutral")
    embedding = VectorField(dimensions=EMBEDDING_DIM)

    class Meta:
        db_table = "reference_chunks"
        constraints = [
            models.UniqueConstraint(
                fields=["corpus_version", "chunk_key"], name="unique_chunk_key_per_version"
            ),
        ]

    def __str__(self) -> str:
        """Chunk key and topic."""
        return f"{self.chunk_key} ({self.topic})"


class PipelineCheckResult(models.Model):
    """The result of one automatic corpus check, kept with the version it checked."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corpus_version = models.ForeignKey(
        CorpusVersion, on_delete=models.CASCADE, related_name="check_results"
    )
    check_name = models.CharField(max_length=100)
    passed = models.BooleanField()
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pipeline_check_results"

    def __str__(self) -> str:
        """Check name and outcome."""
        return f"{self.check_name}: {'passed' if self.passed else 'failed'}"
