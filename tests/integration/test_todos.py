import pytest
from fastapi import status
from sqlalchemy import select

from todoapp.models import Todos

NEW_TODO = {"title": "Write tests", "description": "With Testcontainers", "priority": 2}


@pytest.fixture
async def bob(make_user):
    return await make_user("bob")


async def test_requires_token(client):
    response = await client.get("/todos")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_create_and_read_todo(client, user, auth_headers, db_session):
    response = await client.post("/todos", json=NEW_TODO, headers=auth_headers(user))

    assert response.status_code == status.HTTP_201_CREATED
    created = response.json()
    assert created == {**NEW_TODO, "id": created["id"], "complete": False}

    # It was really written, with the caller as owner.
    stored = await db_session.get(Todos, created["id"])
    assert stored is not None and stored.owner_id == user.id

    response = await client.get(f"/todos/{created['id']}", headers=auth_headers(user))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == created


async def test_list_returns_only_own_todos(client, user, bob, make_todo, auth_headers):
    mine = await make_todo(user, "Mine")
    await make_todo(bob, "Bob's")

    response = await client.get("/todos", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert [t["id"] for t in response.json()] == [mine.id]


async def test_update_todo(client, user, make_todo, auth_headers, db_session):
    todo = await make_todo(user)
    changes = {**NEW_TODO, "complete": True}

    response = await client.put(f"/todos/{todo.id}", json=changes, headers=auth_headers(user))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    await db_session.refresh(todo)
    assert (todo.title, todo.complete, todo.priority) == ("Write tests", True, 2)


async def test_delete_todo(client, user, make_todo, auth_headers, db_session):
    todo = await make_todo(user)

    response = await client.delete(f"/todos/{todo.id}", headers=auth_headers(user))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await db_session.scalar(select(Todos).where(Todos.id == todo.id)) is None


@pytest.mark.parametrize(("method", "body"), [("GET", None), ("PUT", NEW_TODO), ("DELETE", None)])
async def test_other_users_todo_is_not_found(
    client, user, bob, make_todo, auth_headers, db_session, method, body
):
    bobs_todo = await make_todo(bob, "Bob's secret")

    response = await client.request(
        method, f"/todos/{bobs_todo.id}", json=body, headers=auth_headers(user)
    )

    # 404, not 403: other users' todo ids aren't revealed.
    assert response.status_code == status.HTTP_404_NOT_FOUND
    await db_session.refresh(bobs_todo)
    assert bobs_todo.title == "Bob's secret"


async def test_missing_todo_is_not_found(client, user, auth_headers):
    response = await client.get("/todos/999999", headers=auth_headers(user))
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_tables_are_empty_at_test_start(db_session):
    # Guards the rollback-per-test isolation: earlier tests' rows must not leak.
    assert (await db_session.scalars(select(Todos))).all() == []
