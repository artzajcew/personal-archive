from tests.conftest import auth_headers


def test_create_and_list_items(client):
    account = auth_headers(client, username="item_user", email="item@example.com")

    folder = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "item-folder"},
    )
    folder_id = folder.json()["folder"]["id"]

    created = client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Quarterly report",
            "item_type": "document",
            "folder_id": folder_id,
            "description": "Summary of the quarter",
            "content": "Some content",
        },
    )
    assert created.status_code == 201
    assert created.json()["title"] == "Quarterly report"

    listing = client.get("/items?item_type=document", headers=account["headers"])
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 1
    assert any(item["title"] == "Quarterly report" for item in payload["items"])

    search = client.get("/items?q=quarterly", headers=account["headers"])
    assert search.status_code == 200
    assert any(item["title"] == "Quarterly report" for item in search.json()["items"])


def test_get_item_update_and_delete(client):
    account = auth_headers(client, username="item_update_user", email="item_update@example.com")

    response = client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Draft note",
            "item_type": "note",
            "description": "old description",
            "content": "old content",
        },
    )
    item_id = response.json()["id"]

    detail = client.get(f"/items/{item_id}", headers=account["headers"])
    assert detail.status_code == 200
    assert detail.json()["title"] == "Draft note"

    updated = client.patch(
        f"/items/{item_id}",
        headers=account["headers"],
        json={"title": "Updated note", "description": "new description"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated note"

    deleted = client.delete(f"/items/{item_id}", headers=account["headers"])
    assert deleted.status_code == 204

    missing = client.get(f"/items/{item_id}", headers=account["headers"])
    assert missing.status_code == 404


def test_items_root_only_and_folder_access_rules(client):
    account = auth_headers(client, username="item_access_user", email="item_access@example.com")

    root_folder = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Root folder"},
    )
    root_folder_id = root_folder.json()["folder"]["id"]

    client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Root item",
            "item_type": "photo",
            "folder_id": None,
            "content": "root only",
        },
    )

    client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Folder item",
            "item_type": "note",
            "folder_id": root_folder_id,
            "content": "inside folder",
        },
    )

    root_items = client.get("/items?root_only=true", headers=account["headers"])
    assert root_items.status_code == 200
    assert any(item["title"] == "Root item" for item in root_items.json()["items"])

    folder_items = client.get(f"/items?folder_id={root_folder_id}", headers=account["headers"])
    assert folder_items.status_code == 200
    assert any(item["title"] == "Folder item" for item in folder_items.json()["items"])

    invalid_folder = client.get("/items?folder_id=999999", headers=account["headers"])
    assert invalid_folder.status_code == 404
