"""Store raw templates in Supabase Storage through its S3-compatible API."""

import hashlib
import hmac
import logging
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from mbiu.pipeline.errors import StorageError
from mbiu.pipeline.models import StorageMetadata, StoredObject

logger = logging.getLogger(__name__)

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_SUFFIX_RE = re.compile(r"\.[a-z0-9]{1,8}")


def object_key(digest: str, filename: str) -> str:
    """Build the content-addressed key for a raw template.

    Args:
        digest: Hex SHA-256 of the raw file contents.
        filename: Original filename, used only for a safe extension suffix.

    Returns:
        A key shaped like ``raw/<sha256>.pdf``.
    """
    suffix = Path(filename).suffix.lower()
    if not _SUFFIX_RE.fullmatch(suffix):
        suffix = ""
    return f"raw/{digest}{suffix}"


class SupabaseS3Store:
    """Content-addressed, idempotent object storage over the Supabase S3 API."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        client: httpx.Client,
        timeout_s: float = 30.0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """Configure the S3 endpoint, credentials, bucket and signing clock."""
        self._endpoint = endpoint.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._region = region
        self._client = client
        self._timeout_s = timeout_s
        self._now = now or (lambda: datetime.now(UTC))

    def put_if_absent(
        self,
        content: bytes,
        metadata: StorageMetadata,
    ) -> StoredObject:
        """Store ``content`` once, keyed by its SHA-256 hash.

        A HEAD request runs first, so a second pipeline run performs no write.

        Raises:
            StorageError: When the S3 endpoint rejects the HEAD or PUT request.
        """
        digest = hashlib.sha256(content).hexdigest()
        key = object_key(digest, metadata.filename)
        url = self._object_url(key)

        head = self._request("HEAD", url, b"", {})
        if head.status_code == 200:
            logger.info("Raw template %s already stored", key)
            return StoredObject(key=key, sha256=digest, metadata=metadata, created=False)
        if head.status_code != 404:
            raise StorageError(f"Supabase Storage HEAD {key} returned {head.status_code}")

        headers = _metadata_headers(metadata)
        headers["Content-Type"] = metadata.content_type
        put = self._request("PUT", url, content, headers)
        if put.status_code not in (200, 201, 204):
            raise StorageError(f"Supabase Storage PUT {key} returned {put.status_code}")

        logger.info("Stored raw template %s", key)
        return StoredObject(key=key, sha256=digest, metadata=metadata, created=True)

    def _object_url(self, key: str) -> str:
        bucket = quote(self._bucket, safe="")
        return f"{self._endpoint}/{bucket}/{quote(key, safe='/')}"

    def _request(
        self,
        method: str,
        url: str,
        body: bytes,
        headers: Mapping[str, str],
    ) -> httpx.Response:
        payload_hash = hashlib.sha256(body).hexdigest() if body else _EMPTY_SHA256
        signed = _sign_headers(
            method=method,
            url=url,
            headers=headers,
            payload_hash=payload_hash,
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
            now=self._now(),
        )
        try:
            return self._client.request(
                method,
                url,
                headers=signed,
                content=body if method == "PUT" else None,
                timeout=self._timeout_s,
            )
        except httpx.HTTPError as exc:
            raise StorageError(f"Supabase Storage {method} request failed") from exc


def _metadata_headers(metadata: StorageMetadata) -> dict[str, str]:
    values = {
        "source-url": metadata.source_url,
        "document-url": metadata.document_url,
        "fetch-date": metadata.fetched_at.astimezone(UTC).isoformat(),
        "licence": metadata.licence,
        "reviewing-body": metadata.reviewing_body,
        "template-version": metadata.template_version,
        "contract-type": metadata.contract_type,
        "jurisdiction": metadata.jurisdiction,
        "filename": metadata.filename,
    }
    return {f"x-amz-meta-{name}": quote(value, safe="") for name, value in values.items()}


def _sign_headers(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str,
    now: datetime,
) -> dict[str, str]:
    amz_date = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    date_stamp = amz_date[:8]

    to_sign = {name.lower(): " ".join(value.split()) for name, value in headers.items()}
    to_sign["host"] = urlsplit(url).netloc
    to_sign["x-amz-content-sha256"] = payload_hash
    to_sign["x-amz-date"] = amz_date

    signed_names = sorted(to_sign)
    canonical_headers = "".join(f"{name}:{to_sign[name]}\n" for name in signed_names)
    signed_headers = ";".join(signed_names)
    canonical_uri = quote(urlsplit(url).path or "/", safe="/~")
    canonical_request = "\n".join(
        [method.upper(), canonical_uri, "", canonical_headers, signed_headers, payload_hash]
    )

    scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = _signing_key(secret_key, date_stamp, region)
    signature = hmac.new(
        signing_key,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    outgoing = {name: value for name, value in to_sign.items() if name != "host"}
    outgoing["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return outgoing


def _signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    date_key = _hmac(f"AWS4{secret_key}".encode(), date_stamp)
    region_key = _hmac(date_key, region)
    service_key = _hmac(region_key, "s3")
    return _hmac(service_key, "aws4_request")


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
