"""Corpus database models for reviewed standard contract templates.

Zero Contract Storage Invariant:
These tables store ONLY reviewed reference standards, templates, source metadata,
and pipeline verification results. User contracts, extracted text, or analysis
results are NEVER stored in the database.
"""

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models, transaction
from pgvector.django import VectorField


class ReferenceSource(models.Model):
    """Source documents for template standards (e.g. WIPO, Kenya Copyright Act)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=255,
        help_text="Title of the reference document or standard",
    )
    url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="Public URL to the source document",
    )
    license = models.CharField(
        max_length=100,
        help_text="Open or public license allowing reuse",
    )
    reviewing_body = models.CharField(
        max_length=255,
        help_text="Authoritative legal or industry body",
    )
    contract_type = models.CharField(
        max_length=100,
        help_text="Contract type (e.g. recording, management)",
    )
    jurisdiction = models.CharField(
        max_length=50,
        default="KE",
        help_text="Jurisdiction (e.g. KE, international)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reference_sources"
        ordering = ["title"]

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"{self.title} ({self.jurisdiction})"


class CorpusVersion(models.Model):
    """Versioned release of the reference standard corpus.

    Invariant: Only a single version can have is_active=True at any time.
    Published versions are immutable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version_tag = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique version identifier (e.g. v1.0.0)",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this version is the active reference standard",
    )
    embedding_model_id = models.CharField(
        max_length=255,
        default="google/embeddinggemma-2",
        help_text="Embedding model identifier used for this version",
    )
    embedding_dim = models.PositiveIntegerField(
        default=768,
        help_text="Vector dimensionality (must match model)",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when version was published",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "corpus_versions"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_corpus_version",
            ),
        ]

    def __str__(self) -> str:
        """Return human-readable string representation."""
        status = " [ACTIVE]" if self.is_active else ""
        return f"CorpusVersion({self.version_tag}){status}"

    def clean(self) -> None:
        """Validate single active constraint and immutability."""
        super().clean()
        if self.is_active:
            existing = CorpusVersion.objects.filter(is_active=True).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("Only one corpus version can be active at a time.")

        # Published versions cannot change version_tag, embedding_model_id, or embedding_dim
        if self.pk and self.published_at is not None:
            orig = CorpusVersion.objects.filter(pk=self.pk).first()
            if orig and orig.published_at is not None:
                if (
                    orig.version_tag != self.version_tag
                    or orig.embedding_model_id != self.embedding_model_id
                    or orig.embedding_dim != self.embedding_dim
                ):
                    raise ValidationError("Published corpus versions cannot be edited in place.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save instance after running full validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def activate_version(cls, version_tag: str) -> CorpusVersion:
        """Atomically activate a corpus version and deactivate all others."""
        with transaction.atomic():
            target = cls.objects.select_for_update().get(version_tag=version_tag)
            cls.objects.exclude(pk=target.pk).update(is_active=False)
            target.is_active = True
            # Bypass full_clean here since existing active was deactivated above
            super(CorpusVersion, target).save(update_fields=["is_active"])
            return target


class ReferenceChunk(models.Model):
    """A template clause/chunk from a reviewed standard, embedded with pgvector."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corpus_version = models.ForeignKey(
        CorpusVersion,
        on_delete=models.CASCADE,
        related_name="chunks",
        help_text="Corpus version this chunk belongs to",
    )
    source = models.ForeignKey(
        ReferenceSource,
        on_delete=models.CASCADE,
        related_name="chunks",
        null=True,
        blank=True,
        help_text="Source document of this template clause",
    )
    chunk_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional identifier/heading (e.g. Annex A, Clause 4.2)",
    )
    text = models.TextField(help_text="Standard template clause text")
    topic = models.CharField(
        max_length=100,
        help_text="Legal topic (e.g. royalties, rights_assignment)",
    )
    contract_type = models.CharField(
        max_length=100,
        help_text="Contract type (e.g. recording, management)",
    )
    jurisdiction = models.CharField(
        max_length=50,
        default="KE",
        help_text="Jurisdiction of template",
    )
    drafted_for = models.CharField(
        max_length=50,
        default="neutral",
        help_text="Perspective the clause was drafted for (artist, label, neutral)",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured metadata (e.g. section, tags, standard_excerpt)",
    )
    embedding = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        help_text="Vector embedding generated by EmbeddingGemma 2",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reference_chunks"
        ordering = ["corpus_version", "created_at"]

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"ReferenceChunk({self.chunk_key or str(self.id)[:8]}, topic={self.topic})"


class PipelineCheckResult(models.Model):
    """Quality verification check record associated with a corpus version release."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corpus_version = models.ForeignKey(
        CorpusVersion,
        on_delete=models.CASCADE,
        related_name="pipeline_checks",
        help_text="Corpus version evaluated by this check",
    )
    check_name = models.CharField(
        max_length=100,
        help_text="Identifier of the check (e.g. presidio_pii, license_present, deduplication)",
    )
    passed = models.BooleanField(
        default=False,
        help_text="Whether the verification check passed",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed results, metrics, or reasons if check failed",
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pipeline_check_results"
        ordering = ["corpus_version", "-checked_at"]

    def __str__(self) -> str:
        """Return human-readable string representation."""
        status = "PASSED" if self.passed else "FAILED"
        tag = self.corpus_version.version_tag
        return f"PipelineCheck({self.check_name}={status}, version={tag})"
