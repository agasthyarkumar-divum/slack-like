"""Files module tests (architecture.md §8): upload -> (manually-invoked) Celery
processing -> download/thumbnail, plus the access-control rules for
not-yet-attached vs. attached attachments.

No live Celery worker runs during pytest, so these call the task's underlying
async function directly instead of `.delay()` — a standard way to test Celery
task logic without the broker/worker machinery.
"""

import io

from PIL import Image
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Attachment
from app.tests.helpers import auth_header, register_and_login
from app.workers.tasks_files import _process_upload_async


def _png_bytes(size=(64, 64), color=(200, 100, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


async def _process_pending_attachment(db_session, attachment_id: str) -> None:
    """Look up what the service would have passed to process_upload.delay()
    and run the task body directly."""
    result = await db_session.execute(select(Attachment).where(Attachment.id == attachment_id))
    attachment = result.scalar_one()
    pending_key = attachment.storage_uri.removeprefix("pending://")
    temp_path = settings.LOCAL_STORAGE_PATH + f"/_incoming/{attachment_id}.upload"
    await _process_upload_async(
        attachment_id=attachment_id,
        temp_path=temp_path,
        pending_key=pending_key,
        content_type=attachment.mime_type,
    )


async def test_upload_returns_202_processing(client):
    alice = await register_and_login(client, "alice@example.com")
    response = await client.post(
        "/files/upload",
        files={"file": ("note.txt", b"hello file pipeline", "text/plain")},
        headers=auth_header(alice),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["file_name"] == "note.txt"


async def test_upload_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 10)
    alice = await register_and_login(client, "alice@example.com")
    response = await client.post(
        "/files/upload",
        files={"file": ("big.bin", b"x" * 100, "application/octet-stream")},
        headers=auth_header(alice),
    )
    assert response.status_code == 413


async def test_upload_rejects_empty_file(client):
    alice = await register_and_login(client, "alice@example.com")
    response = await client.post(
        "/files/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
        headers=auth_header(alice),
    )
    assert response.status_code == 422


async def test_download_pending_attachment_returns_409(client):
    alice = await register_and_login(client, "alice@example.com")
    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("note.txt", b"still processing", "text/plain")},
            headers=auth_header(alice),
        )
    ).json()

    response = await client.get(f"/files/{uploaded['id']}/download", headers=auth_header(alice))
    assert response.status_code == 409


async def test_unattached_upload_only_visible_to_uploader(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("note.txt", b"mine", "text/plain")},
            headers=auth_header(alice),
        )
    ).json()

    as_bob = await client.get(f"/files/{uploaded['id']}", headers=auth_header(bob))
    as_alice = await client.get(f"/files/{uploaded['id']}", headers=auth_header(alice))
    assert as_bob.status_code == 404
    assert as_alice.status_code == 200


async def test_full_pipeline_text_file_compresses_and_downloads(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    original_bytes = b"compress me " * 500  # repetitive text — zstandard should shrink it

    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("note.txt", original_bytes, "text/plain")},
            headers=auth_header(alice),
        )
    ).json()

    await _process_pending_attachment(db_session, uploaded["id"])

    status_check = await client.get(f"/files/{uploaded['id']}", headers=auth_header(alice))
    assert status_check.json()["status"] == "ready"
    assert status_check.json()["is_compressed"] is True

    downloaded = await client.get(f"/files/{uploaded['id']}/download", headers=auth_header(alice))
    assert downloaded.status_code == 200
    assert downloaded.content == original_bytes
    assert downloaded.headers["content-type"].startswith("text/plain")


async def test_image_upload_generates_a_thumbnail(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    image_bytes = _png_bytes()

    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("photo.png", image_bytes, "image/png")},
            headers=auth_header(alice),
        )
    ).json()

    await _process_pending_attachment(db_session, uploaded["id"])

    status_check = await client.get(f"/files/{uploaded['id']}", headers=auth_header(alice))
    assert status_check.json()["has_thumbnail"] is True
    assert status_check.json()["is_compressed"] is False  # images are skipped, not re-compressed

    thumb = await client.get(f"/files/{uploaded['id']}/thumbnail", headers=auth_header(alice))
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"

    original = await client.get(f"/files/{uploaded['id']}/download", headers=auth_header(alice))
    assert original.status_code == 200
    assert original.content == image_bytes  # download still returns the untouched original


async def test_attaching_to_a_message_extends_access_to_channel_members(client, db_session):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    stranger = await register_and_login(client, "stranger@example.com")
    bob_id = (await client.get("/users/me", headers=auth_header(bob))).json()["id"]

    channel = (
        await client.post(
            "/channels",
            json={"name": "files-test", "type": "public", "member_ids": [bob_id]},
            headers=auth_header(alice),
        )
    ).json()

    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("photo.png", _png_bytes(), "image/png")},
            headers=auth_header(alice),
        )
    ).json()
    await _process_pending_attachment(db_session, uploaded["id"])

    message = (
        await client.post(
            f"/channels/{channel['id']}/messages",
            json={"content": None, "attachment_ids": [uploaded["id"]]},
            headers=auth_header(alice),
        )
    ).json()
    assert message["attachment_ids"] == [uploaded["id"]]

    as_bob = await client.get(f"/files/{uploaded['id']}/download", headers=auth_header(bob))
    as_stranger = await client.get(f"/files/{uploaded['id']}/download", headers=auth_header(stranger))
    assert as_bob.status_code == 200
    assert as_stranger.status_code == 404


async def test_cannot_attach_someone_elses_upload(client):
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    channel = (
        await client.post(
            "/channels", json={"name": "c", "type": "public", "member_ids": []},
            headers=auth_header(bob),
        )
    ).json()
    uploaded = (
        await client.post(
            "/files/upload",
            files={"file": ("note.txt", b"alices file", "text/plain")},
            headers=auth_header(alice),
        )
    ).json()

    response = await client.post(
        f"/channels/{channel['id']}/messages",
        json={"content": None, "attachment_ids": [uploaded["id"]]},
        headers=auth_header(bob),
    )
    assert response.status_code == 422


async def test_message_requires_content_or_attachment(client):
    alice = await register_and_login(client, "alice@example.com")
    channel = (
        await client.post(
            "/channels", json={"name": "c", "type": "public", "member_ids": []},
            headers=auth_header(alice),
        )
    ).json()

    response = await client.post(
        f"/channels/{channel['id']}/messages", json={"content": None}, headers=auth_header(alice)
    )
    assert response.status_code == 422
