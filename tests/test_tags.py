from tests.conftest import auth_headers


def test_create_and_list_tags(client):
    account = auth_headers(client, username="tag_user", email="tag@example.com")

    created = client.post(
        "/tags",
        headers=account["headers"],
        json={"name": "urgent"},
    )
    assert created.status_code == 201
    assert created.json()["name"] == "urgent"

    response = client.get("/tags", headers=account["headers"])
    assert response.status_code == 200
    payload = response.json()
    assert any(tag["name"] == "urgent" for tag in payload)


def test_update_tag_and_duplicate_name_conflict(client):
    account = auth_headers(client, username="tag_update_user", email="tag_update@example.com")

    created = client.post(
        "/tags",
        headers=account["headers"],
        json={"name": "finance"},
    )
    tag_id = created.json()["id"]

    updated = client.patch(
        f"/tags/{tag_id}",
        headers=account["headers"],
        json={"name": "budget"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "budget"

    duplicate = client.post(
        "/tags",
        headers=account["headers"],
        json={"name": "budget"},
    )
    assert duplicate.status_code == 409


def test_attach_tag_to_item_and_list_item_tags(client):
    account = auth_headers(client, username="tag_item_user", email="tag_item@example.com")

    item = client.post(
        "/items",
        headers=account["headers"],
        json={
            "title": "Tagged item",
            "item_type": "document",
            "description": "with tags",
            "content": "This item is tagged",
        },
    )
    item_id = item.json()["id"]

    tag = client.post(
        "/tags",
        headers=account["headers"],
        json={"name": "work"},
    )
    tag_id = tag.json()["id"]

    attach = client.post(
        f"/items/{item_id}/tags/{tag_id}",
        headers=account["headers"],
    )
    assert attach.status_code == 201

    item_tags = client.get(f"/items/{item_id}/tags", headers=account["headers"])
    assert item_tags.status_code == 200
    assert any(tag_payload["name"] == "work" for tag_payload in item_tags.json())

    detach = client.delete(f"/items/{item_id}/tags/{tag_id}", headers=account["headers"])
    assert detach.status_code == 204


def test_delete_tag(client):
    account = auth_headers(client, username="tag_delete_user", email="tag_delete@example.com")

    created = client.post(
        "/tags",
        headers=account["headers"],
        json={"name": "archive"},
    )
    tag_id = created.json()["id"]

    deleted = client.delete(f"/tags/{tag_id}", headers=account["headers"])
    assert deleted.status_code == 204

    missing = client.get("/tags", headers=account["headers"])
    assert all(tag["name"] != "archive" for tag in missing.json())
