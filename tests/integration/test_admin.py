from fastapi import status

from todoapp.models import Todos


async def test_admin_requires_token(client):
    response = await client.get("/admin/todos")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_admin_forbidden_for_regular_user(client, user, auth_headers):
    response = await client.get("/admin/todos", headers=auth_headers(user))
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_admin_sees_all_todos(client, admin, user, make_user, make_todo, auth_headers):
    bob = await make_user("bob")
    ids = {(await make_todo(user)).id, (await make_todo(bob)).id}

    response = await client.get("/admin/todos", headers=auth_headers(admin))

    assert response.status_code == status.HTTP_200_OK
    assert {t["id"] for t in response.json()} == ids


async def test_admin_deletes_any_todo(client, admin, user, make_todo, auth_headers, db_session):
    todo = await make_todo(user)

    response = await client.delete(f"/admin/todos/{todo.id}", headers=auth_headers(admin))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await db_session.get(Todos, todo.id, populate_existing=True) is None


async def test_admin_delete_missing_todo(client, admin, auth_headers):
    response = await client.delete("/admin/todos/999999", headers=auth_headers(admin))
    assert response.status_code == status.HTTP_404_NOT_FOUND
