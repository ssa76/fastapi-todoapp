from fastapi import status

NEW_USER = {
    "username": "bob",
    "email": "bob@example.com",
    "first_name": "Bob",
    "last_name": "Builder",
    "password": "s3cret-password",
}


async def test_register_user(client):
    response = await client.post("/auth", json=NEW_USER)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["username"] == "bob"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body


async def test_register_cannot_choose_role(client):
    response = await client.post("/auth", json={**NEW_USER, "role": "admin"})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["role"] == "user"


async def test_register_duplicate_username_is_conflict(client, user):
    response = await client.post(
        "/auth", json={**NEW_USER, "username": user.username, "email": "other@example.com"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


async def test_register_duplicate_email_is_conflict(client, user):
    response = await client.post("/auth", json={**NEW_USER, "email": user.email})
    assert response.status_code == status.HTTP_409_CONFLICT


async def test_session_usable_after_conflict(client, user):
    # The 409 path rolls back; the same request session must still work afterwards.
    await client.post("/auth", json={**NEW_USER, "username": user.username})
    response = await client.post("/auth", json=NEW_USER)
    assert response.status_code == status.HTTP_201_CREATED


async def test_login_returns_working_token(client, user, password):
    response = await client.post(
        "/auth/token", data={"username": user.username, "password": password}
    )

    assert response.status_code == status.HTTP_200_OK
    token = response.json()
    assert token["token_type"] == "bearer"

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["username"] == user.username


async def test_login_wrong_password(client, user):
    response = await client.post(
        "/auth/token", data={"username": user.username, "password": "wrong-password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_login_unknown_user(client, password):
    response = await client.post("/auth/token", data={"username": "nobody", "password": password})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_inactive_user_token_rejected(client, make_user, auth_headers):
    inactive = await make_user("ghost", is_active=False)
    response = await client.get("/users/me", headers=auth_headers(inactive))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_garbage_token_rejected(client):
    response = await client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
