import pytest
from fastapi import status
from fastapi.testclient import TestClient

import todoapp.main as main

client = TestClient(main.app)


@pytest.mark.parametrize(
    ("path", "form_id"), [("/login", "loginForm"), ("/register", "registerForm")]
)
def test_auth_pages_render_inside_layout(path, form_id):
    response = client.get(path)

    assert response.status_code == status.HTTP_200_OK
    html = response.text
    assert f'id="{form_id}"' in html
    # One document, with the form inside <body> (not appended after </html>).
    assert html.count("<html") == 1
    assert html.index(form_id) < html.index("</body>")
    assert "/static/js/base.js" in html


def test_home_page():
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/html")


def test_static_files_are_served():
    response = client.get("/static/css/base.css")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/css")


def test_todo_page_without_cookie_redirects_to_login():
    # No database access: a missing cookie is rejected before any query.
    response = client.get("/todos-page", follow_redirects=False)

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/login"


def test_pages_are_not_in_api_docs():
    paths = client.get("/openapi.json").json()["paths"]
    assert not {"/", "/login", "/register", "/todos-page"} & paths.keys()
