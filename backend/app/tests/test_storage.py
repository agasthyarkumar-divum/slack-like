"""StorageBackend tests (architecture.md §2): the local backend's encrypt-at-rest
behavior and path-traversal guard, plus the factory's backend selection and the
S3 stub's NotImplementedError contract.
"""

import io

import pytest
from cryptography.fernet import Fernet

from app.storage.factory import get_storage_backend
from app.storage.local import LocalFileSystemBackend
from app.storage.s3_ready import S3Backend

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture()
def backend(tmp_path):
    return LocalFileSystemBackend(base_path=str(tmp_path), encryption_key=TEST_KEY)


async def test_save_load_roundtrip(backend):
    uri = await backend.save("avatars/alice.png", io.BytesIO(b"plaintext image bytes"), "image/png")
    assert uri == "local://avatars/alice.png"
    assert await backend.load("avatars/alice.png") == b"plaintext image bytes"


async def test_data_is_encrypted_at_rest(backend, tmp_path):
    await backend.save("secret.txt", io.BytesIO(b"hello world"), "text/plain")
    raw_bytes_on_disk = (tmp_path / "secret.txt").read_bytes()
    assert b"hello world" not in raw_bytes_on_disk


async def test_load_missing_key_raises(backend):
    with pytest.raises(FileNotFoundError):
        await backend.load("does/not/exist.txt")


async def test_delete_removes_the_file(backend, tmp_path):
    await backend.save("to-delete.txt", io.BytesIO(b"bye"), "text/plain")
    assert (tmp_path / "to-delete.txt").exists()

    await backend.delete("to-delete.txt")
    assert not (tmp_path / "to-delete.txt").exists()


async def test_delete_is_idempotent(backend):
    await backend.delete("never-existed.txt")  # must not raise


async def test_get_presigned_url_returns_none(backend):
    await backend.save("f.txt", io.BytesIO(b"x"), "text/plain")
    assert await backend.get_presigned_url("f.txt") is None


async def test_path_traversal_is_rejected(backend):
    with pytest.raises(ValueError):
        await backend.save("../../etc/passwd", io.BytesIO(b"pwned"), "text/plain")


async def test_missing_encryption_key_fails_fast(tmp_path, monkeypatch):
    # encryption_key="" falls back to settings.FILE_ENCRYPTION_KEY (by design —
    # an empty override shouldn't silently disable the settings-based key), so
    # to actually exercise "no key available anywhere" both sources must be empty.
    monkeypatch.setattr("app.storage.local.settings.FILE_ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError, match="FILE_ENCRYPTION_KEY"):
        LocalFileSystemBackend(base_path=str(tmp_path))


def test_factory_selects_local_backend(monkeypatch):
    monkeypatch.setattr("app.storage.factory.settings.STORAGE_BACKEND", "local")
    get_storage_backend.cache_clear()
    assert isinstance(get_storage_backend(), LocalFileSystemBackend)


def test_factory_selects_s3_backend(monkeypatch):
    monkeypatch.setattr("app.storage.factory.settings.STORAGE_BACKEND", "s3")
    get_storage_backend.cache_clear()
    assert isinstance(get_storage_backend(), S3Backend)
    get_storage_backend.cache_clear()  # don't leak the s3 selection into other tests


def test_factory_rejects_unknown_backend(monkeypatch):
    monkeypatch.setattr("app.storage.factory.settings.STORAGE_BACKEND", "azure")
    get_storage_backend.cache_clear()
    with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
        get_storage_backend()
    get_storage_backend.cache_clear()


async def test_s3_backend_methods_all_raise_not_implemented():
    backend = S3Backend()
    with pytest.raises(NotImplementedError):
        await backend.save("k", io.BytesIO(b"x"), "text/plain")
    with pytest.raises(NotImplementedError):
        await backend.load("k")
    with pytest.raises(NotImplementedError):
        await backend.delete("k")
    with pytest.raises(NotImplementedError):
        await backend.get_presigned_url("k")
