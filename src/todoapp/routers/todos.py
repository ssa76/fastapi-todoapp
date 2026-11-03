from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select

from todoapp.database import DbSession
from todoapp.models import Todos
from todoapp.routers.auth import CurrentUser
from todoapp.schemas import TodoRead, TodoRequest


async def get_todo(db: DbSession, user: CurrentUser, todo_id: Annotated[int, Path(gt=0)]) -> Todos:
    """Load one of the current user's todos, or 404.

    Depending on CurrentUser here means the token is checked before the lookup, so a
    request without a valid token always gets 401 (it can't probe which ids exist).
    Someone else's todo is a 404, not 403, so its existence isn't revealed either.
    """
    stmt = select(Todos).where(Todos.id == todo_id, Todos.owner_id == user.id)
    todo = await db.scalar(stmt)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")
    return todo


TodoDep = Annotated[Todos, Depends(get_todo)]


router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoRead])
async def list_todos(db: DbSession, user: CurrentUser):
    stmt = select(Todos).where(Todos.owner_id == user.id)
    return (await db.scalars(stmt)).all()


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo_by_id(todo: TodoDep):
    return todo


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(db: DbSession, body: TodoRequest, user: CurrentUser):
    todo = Todos(**body.model_dump(), owner_id=user.id)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@router.put("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: DbSession, todo: TodoDep, body: TodoRequest):
    for field, value in body.model_dump().items():
        setattr(todo, field, value)
    await db.commit()


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: DbSession, todo: TodoDep):
    await db.delete(todo)
    await db.commit()
