from fastapi import status


async def test_get_me(client, user, auth_headers):
    response = await client.get("/users/me", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == user.email
    assert "hashed_password" not in response.json()


async def test_change_password(client, user, password, auth_headers):
    new_password = "a-brand-new-password"
    response = await client.put(
        "/users/me/password",
        json={"current_password": password, "new_password": new_password},
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    old_login = await client.post(
        "/auth/token", data={"username": user.username, "password": password}
    )
    new_login = await client.post(
        "/auth/token", data={"username": user.username, "password": new_password}
    )
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_login.status_code == status.HTTP_200_OK


async def test_change_password_wrong_current(client, user, auth_headers):
    response = await client.put(
        "/users/me/password",
        json={"current_password": "not-my-password", "new_password": "a-brand-new-password"},
        headers=auth_headers(user),
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
