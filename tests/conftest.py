from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_connection, get_db
from app.main import app


@pytest.fixture()
def db():
    conn = get_connection()
    conn.autocommit = True

    with conn.cursor() as cursor:
        cursor.execute(
            """
            TRUNCATE TABLE item_tags, archive_items, tags, folders, revoked_tokens, users
            RESTART IDENTITY CASCADE
            """
        )

    yield conn

    with conn.cursor() as cursor:
        cursor.execute(
            """
            TRUNCATE TABLE item_tags, archive_items, tags, folders, revoked_tokens, users
            RESTART IDENTITY CASCADE
            """
        )

    conn.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def register_user(client, *, username=None, email=None, password="StrongPass123"):
    username = username or f"user_{uuid4().hex[:8]}"
    email = email or f"{username}@example.com"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text

    return {
        "username": username,
        "email": email,
        "password": password,
        "user": response.json()["user"],
    }


def login_user(client, identifier, password):
    response = client.post(
        "/auth/login",
        json={
            "identifier": identifier,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(client, *, username=None, email=None, password="StrongPass123"):
    account = register_user(client, username=username, email=email, password=password)
    token_data = login_user(client, account["username"], account["password"])

    return {
        **account,
        "access_token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
    }
