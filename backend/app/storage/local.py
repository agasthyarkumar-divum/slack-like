"""LocalFileSystemBackend (architecture.md §2) — today's StorageBackend.

Encryption happens here, in the backend implementation, not in the caller —
so callers write plaintext bytes in and read plaintext bytes back, and
swapping to S3Backend later never touches the encryption model (architecture.md
§2: "Encryption stays backend-agnostic... encrypt/decrypt happens in the
service layer before handing bytes to whichever StorageBackend is active").
Concretely: LocalFileSystemBackend is itself that "service-layer" boundary
today, since local disk has no server-side encryption of its own the way S3
does — the encrypt/decrypt call sites just live here instead of one layer up.
"""

from pathlib import Path
from typing import BinaryIO

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.storage.base import StorageBackend


class LocalFileSystemBackend(StorageBackend):
    def __init__(self, base_path: str | None = None, encryption_key: str | None = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH).resolve()
        key = encryption_key or settings.FILE_ENCRYPTION_KEY
        if not key:
            raise RuntimeError(
                "FILE_ENCRYPTION_KEY is not set. Generate one with: "
                'python3 -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        self._fernet = Fernet(key)

    def _resolve(self, key: str) -> Path:
        """Resolves `key` under base_path and rejects anything that would
        escape it (e.g. '../../etc/passwd') — keys are meant to be
        server-generated, but this is cheap insurance against path traversal.
        """
        path = (self.base_path / key).resolve()
        if self.base_path not in path.parents and path != self.base_path:
            raise ValueError(f"storage key resolves outside the storage root: {key!r}")
        return path

    async def save(self, key: str, data: BinaryIO, content_type: str) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = self._fernet.encrypt(data.read())
        path.write_bytes(encrypted)
        return f"local://{key}"

    async def load(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        try:
            return self._fernet.decrypt(path.read_bytes())
        except InvalidToken as exc:
            raise ValueError(f"stored data for {key!r} failed integrity/decryption check") from exc

    async def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        return None  # no direct URL possible; client hits /files/{id}/download instead
