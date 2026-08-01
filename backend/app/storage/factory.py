from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local import LocalFileSystemBackend
from app.storage.s3_ready import S3Backend

_BACKENDS: dict[str, type[StorageBackend]] = {
    "local": LocalFileSystemBackend,
    "s3": S3Backend,
}


@lru_cache
def get_storage_backend() -> StorageBackend:
    """FastAPI dependency (Depends(get_storage_backend)) once files routes land
    in Phase 7 — every upload/download/thumbnail call site injects this rather
    than importing a concrete backend directly (architecture.md §2).
    """
    try:
        backend_cls = _BACKENDS[settings.STORAGE_BACKEND]
    except KeyError as exc:
        raise ValueError(
            f"Unknown STORAGE_BACKEND {settings.STORAGE_BACKEND!r}; "
            f"expected one of {sorted(_BACKENDS)}"
        ) from exc
    return backend_cls()
