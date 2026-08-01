"""The StorageBackend interface (architecture.md §2). Every file-touching code
path in the app goes through this — nothing outside app/storage/ ever calls
open() or a filesystem path directly.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: BinaryIO, content_type: str) -> str:
        """Returns a storage URI, e.g. 'local://uploads/abc.enc' or 's3://bucket/abc.enc'."""

    @abstractmethod
    async def load(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Local backend returns None (use the API proxy download route); S3
        backend returns a real presigned URL."""
