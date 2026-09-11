"""MinIO / S3-compatible object store.

Falls back to a local filesystem store when MinIO is not configured.
This keeps the core pipeline functional offline.
"""
from __future__ import annotations

import io
import os
import threading
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.object_store import ObjectStore

log = get_logger(__name__)


class LocalFileStore(ObjectStore):
    def __init__(self, base_dir: str = "./data/raw"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.base_dir / key).resolve()
        if not str(p).startswith(str(self.base_dir.resolve())):
            raise ValueError("Path traversal detected")
        return p

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return f"local://{p}"

    def get_bytes(self, key: str) -> bytes:
        with open(self._path(key), "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def health(self) -> dict:
        return {"backend": "local", "base_dir": str(self.base_dir), "ok": self.base_dir.exists()}


class MinIOStore(ObjectStore):
    def __init__(self) -> None:
        from minio import Minio
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
        self._bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket, location=settings.MINIO_REGION)
                log.info("minio.bucket.created", bucket=self._bucket)
        except Exception as e:
            log.warning("minio.ensure_bucket_failed", error=str(e))
            raise

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._client.put_object(
            self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type,
        )
        return f"minio://{self._bucket}/{key}"

    def get_bytes(self, key: str) -> bytes:
        resp = None
        try:
            resp = self._client.get_object(self._bucket, key)
            return resp.read()
        finally:
            if resp is not None:
                resp.close()
                resp.release_conn()

    def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except Exception:
            return False

    def health(self) -> dict:
        try:
            ok = self._client.bucket_exists(self._bucket)
            return {"backend": "minio", "endpoint": settings.MINIO_ENDPOINT, "bucket": self._bucket, "ok": bool(ok)}
        except Exception as e:
            return {"backend": "minio", "endpoint": settings.MINIO_ENDPOINT, "bucket": self._bucket, "ok": False, "error": str(e)}


_store: ObjectStore | None = None
_lock = threading.Lock()


def get_object_store() -> ObjectStore:
    global _store
    if _store is not None:
        return _store
    with _lock:
        if _store is not None:
            return _store
        if settings.MINIO_ENDPOINT:
            try:
                _store = MinIOStore()
                log.info("storage.backend", backend="minio", endpoint=settings.MINIO_ENDPOINT)
                return _store
            except Exception as e:
                log.warning("storage.minio_failed_fallback_local", error=str(e))
        _store = LocalFileStore()
        log.info("storage.backend", backend="local")
        return _store