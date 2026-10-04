from tests.conftest import auth_headers, login_user, register_user


def test_register_user_success(client):
    username = "alpha_user"
    email = "alpha@example.com"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["message"] == "Registration successful"
    assert payload["user"]["username"] == username
    assert payload["user"]["email"] == email


def test_register_user_duplicate_email_or_username_fails(client):
    account = register_user(client, username="dup_user", email="dup@example.com")

    response = client.post(
        "/auth/register",
        json={
            "username": account["username"],
            "email": "another@example.com",
            "password": "StrongPass123",
        },
    )
    assert response.status_code == 409

    response = client.post(
        "/auth/register",
        json={
            "username": "another_name",
            "email": account["email"],
            "password": "StrongPass123",
        },
    )
    assert response.status_code == 409


def test_login_returns_access_token(client):
    account = register_user(client, username="login_user", email="login@example.com")

    response = client.post(
        "/auth/login",
        json={
            "identifier": account["username"],
            "password": account["password"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["expires_at"]


def test_get_profile_and_update_profile(client):
    account = auth_headers(client, username="profile_user", email="profile@example.com")
    other = register_user(client, username="other_profile_user", email="other_profile@example.com")

    me_response = client.get("/auth/me", headers=account["headers"])
    assert me_response.status_code == 200
    assert me_response.json()["user"]["username"] == "profile_user"

    updated = client.patch(
        "/auth/me",
        headers=account["headers"],
        json={"username": "profile_user_updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["username"] == "profile_user_updated"

    duplicate = client.patch(
        "/auth/me",
        headers=account["headers"],
        json={"email": other["email"]},
    )
    assert duplicate.status_code == 409


def test_change_password_and_logout_revoke_token(client):
    account = auth_headers(client, username="password_user", email="password@example.com")

    response = client.patch(
        "/auth/password",
        headers=account["headers"],
        json={
            "current_password": account["password"],
            "new_password": "NewStrongPass456",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"]

    new_login = login_user(client, account["username"], "NewStrongPass456")
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {new_login['access_token']}"},
    )
    assert logout_response.status_code == 200

    me_after_logout = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_login['access_token']}"},
    )
    assert me_after_logout.status_code == 401


def test_delete_account(client):
    account = auth_headers(client, username="delete_user", email="delete@example.com")

    response = client.delete("/auth/me", headers=account["headers"])
    assert response.status_code == 204

    follow_up = client.get("/auth/me", headers=account["headers"])
    assert follow_up.status_code == 401
