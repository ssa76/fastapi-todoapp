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


def test_root_redirects_to_todo_page():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/todos-page"


@pytest.mark.parametrize(("path", "title"), [("/login", "Login"), ("/register", "Register")])
def test_pages_have_their_own_title(path, title):
    assert f"<title>{title} · Todo App</title>" in client.get(path).text


def test_register_form_matches_the_api():
    html = client.get("/register").text

    assert 'name="role"' not in html  # the server always assigns "user"
    phone = html[html.index('name="phone_number"') :].split("/>")[0]
    assert "required" not in phone  # optional
    password = html[html.index('name="password"') :].split("/>")[0]
    assert 'minlength="8"' in password


def test_base_css_loads_after_bootstrap():
    # Otherwise Bootstrap's body color/background override ours.
    html = client.get("/login").text
    assert html.index("bootstrap.min.css") < html.index("css/base.css")


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
