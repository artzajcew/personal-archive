from tests.conftest import auth_headers


def test_create_and_list_folders(client):
    account = auth_headers(client, username="folder_user", email="folder@example.com")

    created = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Projects"},
    )
    assert created.status_code == 201
    folder_id = created.json()["folder"]["id"]

    nested = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Backend", "parent_folder_id": folder_id},
    )
    assert nested.status_code == 201

    listing = client.get("/folders", headers=account["headers"])
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["count"] >= 2
    assert any(item["name"] == "Projects" for item in payload["folders"])

    child_listing = client.get(
        "/folders?parent_folder_id=1",
        headers=account["headers"],
    )
    assert child_listing.status_code == 200
    assert child_listing.json()["count"] >= 1


def test_get_folder_update_and_delete(client):
    account = auth_headers(client, username="folder_update_user", email="folder_update@example.com")

    created = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Old Name"},
    )
    folder_id = created.json()["folder"]["id"]

    detail = client.get(f"/folders/{folder_id}", headers=account["headers"])
    assert detail.status_code == 200
    assert detail.json()["folder"]["name"] == "Old Name"

    updated = client.patch(
        f"/folders/{folder_id}",
        headers=account["headers"],
        json={"name": "New Name"},
    )
    assert updated.status_code == 200
    assert updated.json()["folder"]["name"] == "New Name"

    deleted = client.delete(f"/folders/{folder_id}", headers=account["headers"])
    assert deleted.status_code == 204

    missing = client.get(f"/folders/{folder_id}", headers=account["headers"])
    assert missing.status_code == 404


def test_folder_cycle_and_parent_validation(client):
    account = auth_headers(client, username="folder_cycle_user", email="folder_cycle@example.com")

    root = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Root"},
    )
    root_id = root.json()["folder"]["id"]

    child = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Child", "parent_folder_id": root_id},
    )
    child_id = child.json()["folder"]["id"]

    cycle = client.patch(
        f"/folders/{root_id}",
        headers=account["headers"],
        json={"parent_folder_id": root_id},
    )
    assert cycle.status_code == 400

    invalid_parent = client.post(
        "/folders",
        headers=account["headers"],
        json={"name": "Ghost", "parent_folder_id": 999999},
    )
    assert invalid_parent.status_code == 404

    move_to_child = client.patch(
        f"/folders/{root_id}",
        headers=account["headers"],
        json={"parent_folder_id": child_id},
    )
    assert move_to_child.status_code == 400
