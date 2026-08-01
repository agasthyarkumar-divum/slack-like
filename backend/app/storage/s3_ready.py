"""S3Backend — stub, implement on demand (architecture.md §2, §14: trigger is
"Storage >500GB or need CDN"). Drop-in replacement once implemented: same
interface, zero call-site changes required. Works with AWS S3, MinIO,
Backblaze B2, Cloudflare R2, or any S3-compatible API — which is itself an
option if "not paid AWS" matters more than "not S3-compatible".
"""

from typing import BinaryIO

from app.storage.base import StorageBackend


class S3Backend(StorageBackend):
    async def save(self, key: str, data: BinaryIO, content_type: str) -> str:
        raise NotImplementedError

    async def load(self, key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        raise NotImplementedError
