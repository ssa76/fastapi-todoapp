from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from todoapp.database import DbSession
from todoapp.models import Todos, Users
from todoapp.routers.auth import get_current_user
from todoapp.templating import templates

# HTML pages for the browser. Kept out of the OpenAPI schema (/docs), which documents
# the JSON API only. Page URLs deliberately don't share the API's prefixes (/auth, /todos):
# a page at /todos/todo-page would be captured by the API route /todos/{todo_id}.
router = APIRouter(tags=["pages"], include_in_schema=False)

ACCESS_TOKEN_COOKIE = "access_token"  # set by static/js/base.js after a successful login


async def get_page_user(
    db: DbSession,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
) -> Users | None:
    """The logged-in user from the access token cookie, or None.

    Pages redirect to the login page instead of answering 401 like the API, so an invalid,
    expired or missing token becomes None. Other errors (database down, ...) still raise.
    """
    if not access_token:
        return None
    try:
        return await get_current_user(db, access_token)
    except HTTPException:
        return None


PageUser = Annotated[Users | None, Depends(get_page_user)]


def redirect_to_login() -> RedirectResponse:
    # 303: the browser follows it with a GET, whatever the original method was.
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ACCESS_TOKEN_COOKIE)  # drop a stale or invalid token
    return response


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/todos-page", status_code=status.HTTP_302_FOUND)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@router.get("/todos-page", response_class=HTMLResponse)
async def todo_page(request: Request, db: DbSession, user: PageUser):
    if user is None:
        return redirect_to_login()

    stmt = select(Todos).where(Todos.owner_id == user.id).order_by(Todos.id)
    todos = (await db.scalars(stmt)).all()
    return templates.TemplateResponse(request, "todo.html", {"user": user, "todos": todos})


@router.get("/add-todos-page", response_class=HTMLResponse)
async def add_todo_page(request: Request, user: PageUser):
    if user is None:
        return redirect_to_login()

    return templates.TemplateResponse(request, "add.html", {"user": user})


@router.get("/edit-todos-page/{todo_id}", response_class=HTMLResponse)
async def edit_todo_page(
    request: Request, db: DbSession, user: PageUser, todo_id: Annotated[int, Path(gt=0)]
):
    if user is None:
        return redirect_to_login()

    # Someone else's todo is a 404 too, like the API: its existence isn't revealed.
    stmt = select(Todos).where(Todos.id == todo_id, Todos.owner_id == user.id)
    todo = await db.scalar(stmt)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")

    return templates.TemplateResponse(request, "edit.html", {"user": user, "todo": todo})
