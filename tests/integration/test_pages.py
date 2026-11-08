from fastapi import status

from todoapp.routers.auth import create_access_token


def login(client, user) -> None:
    # What static/js/base.js does after a successful login.
    client.cookies.set("access_token", create_access_token(user))


async def test_todo_page_lists_only_own_todos(client, user, make_user, make_todo):
    bob = await make_user("bob")
    await make_todo(user, "Alice's task")
    await make_todo(bob, "Bob's task")
    login(client, user)

    response = await client.get("/todos-page")

    assert response.status_code == status.HTTP_200_OK
    assert "Alice&#39;s task" in response.text
    assert "Bob&#39;s task" not in response.text


async def test_todo_page_with_invalid_cookie_redirects_and_clears_it(client):
    client.cookies.set("access_token", "not-a-jwt")

    response = await client.get("/todos-page", follow_redirects=False)

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/login"
    assert 'access_token=""' in response.headers["set-cookie"]  # deletes the cookie


async def test_todo_page_for_inactive_user_redirects(client, make_user):
    login(client, await make_user("ghost", is_active=False))

    response = await client.get("/todos-page", follow_redirects=False)

    assert response.status_code == status.HTTP_303_SEE_OTHER


async def test_page_routes_dont_shadow_the_api(client, user, make_todo, auth_headers):
    todo = await make_todo(user)

    response = await client.get(f"/todos/{todo.id}", headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == todo.id


async def test_todo_page_marks_completed_todos(client, user, make_todo):
    await make_todo(user, "Done task", complete=True)
    await make_todo(user, "Open task")
    login(client, user)

    html = (await client.get("/todos-page")).text

    assert '<tr class="table-success">' in html
    assert '<td class="strike-through-td">Done task</td>' in html
    assert '<td class="">Open task</td>' in html
    assert 'href="http://test/todos-page">Home</a>' in html  # navbar link


async def test_add_page_requires_login(client):
    response = await client.get("/add-todos-page", follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER


async def test_add_page_renders_form(client, user):
    login(client, user)

    response = await client.get("/add-todos-page")

    assert response.status_code == status.HTTP_200_OK
    assert 'id="todoForm"' in response.text


async def test_edit_page_prefills_todo(client, user, make_todo):
    todo = await make_todo(user, "Fix bike", priority=4, complete=True)
    login(client, user)

    response = await client.get(f"/edit-todos-page/{todo.id}")

    assert response.status_code == status.HTTP_200_OK
    html = response.text
    assert 'value="Fix bike"' in html
    assert '<option value="4" selected>4</option>' in html
    assert html.count("selected>") == 1  # only the todo's priority
    assert 'name="complete"\n                        checked' in html
    assert 'id="deleteButton"' in html  # base.js wires this up


async def test_edit_page_for_other_users_todo_is_not_found(client, user, make_user, make_todo):
    bobs_todo = await make_todo(await make_user("bob"))
    login(client, user)

    response = await client.get(f"/edit-todos-page/{bobs_todo.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_edit_page_for_missing_todo_is_not_found(client, user):
    login(client, user)
    response = await client.get("/edit-todos-page/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
