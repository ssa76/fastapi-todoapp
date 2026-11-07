from fastapi import status
from fastapi.testclient import TestClient

import todoapp.main as main

client = TestClient(main.app)


def test_home_page_uses_base_layout():
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "<title>Home · Todo App</title>" in html
    assert 'href="http://testserver/static/css/app.css"' in html  # from base.html
    assert 'class="site-header"' in html  # partials/header.html
    assert "<h1>Todo App</h1>" in html  # home.html's content block


def test_static_files_are_served():
    response = client.get("/static/css/app.css")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("text/css")


def test_pages_are_not_in_api_docs():
    assert "/" not in client.get("/openapi.json").json()["paths"]
