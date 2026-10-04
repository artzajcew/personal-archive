from pathlib import Path

from app.config import settings
from tests.conftest import auth_headers


def test_upload_and_download_file(client, tmp_path):
    account = auth_headers(client, username="file_user", email="file@example.com")

    item = client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "File item",
            "item_type": "document",
            "description": "contains file",
            "content": "text content",
        },
    )
    item_id = item.json()["id"]

    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello from archive", encoding="utf-8")

    with file_path.open("rb") as file:
        upload = client.post(
            f"/files/{item_id}",
            headers=account["headers"],
            files={"file": (file_path.name, file, "text/plain")},
        )

    assert upload.status_code == 201
    assert upload.json()["original_file_name"] == file_path.name

    download = client.get(f"/files/{item_id}", headers=account["headers"])
    assert download.status_code == 200
    assert download.content == b"hello from archive"


def test_rejects_unsupported_file_type(client):
    account = auth_headers(client, username="invalid_file_user", email="invalid_file@example.com")

    item = client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Bad file item",
            "item_type": "document",
        },
    )
    item_id = item.json()["id"]

    response = client.post(
        f"/files/{item_id}",
        headers=account["headers"],
        files={"file": ("bad.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File type is not allowed"


def test_delete_file_removes_uploaded_file(client, tmp_path):
    account = auth_headers(client, username="delete_file_user", email="delete_file@example.com")

    item = client.post(
        "/items",
        headers=account["headers"],
        json={"title": "To delete", "item_type": "document"},
    )
    item_id = item.json()["id"]

    file_path = tmp_path / "archive.txt"
    file_path.write_text("remove me", encoding="utf-8")

    with file_path.open("rb") as file:
        client.post(
            f"/files/{item_id}",
            headers=account["headers"],
            files={"file": (file_path.name, file, "text/plain")},
        )

    delete_response = client.delete(f"/files/{item_id}", headers=account["headers"])
    assert delete_response.status_code == 204

    get_response = client.get(f"/files/{item_id}", headers=account["headers"])
    assert get_response.status_code == 404


def test_upload_rejects_large_files(client, monkeypatch):
    account = auth_headers(client, username="large_file_user", email="large_file@example.com")

    item = client.post(
        "/items",
        headers=account["headers"],
        json={"title": "Large file", "item_type": "document"},
    )
    item_id = item.json()["id"]

    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 1)

    response = client.post(
        f"/files/{item_id}",
        headers=account["headers"],
        files={"file": ("large.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File is too large"

    upload_dir = Path(settings.UPLOAD_DIR)
    for file in upload_dir.iterdir():
        if file.is_file():
            file.unlink()
