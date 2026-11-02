from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select

from todoapp.database import DbSession
from todoapp.models import Todos
from todoapp.schemas import TodoRead, TodoRequest


async def get_todo(db: DbSession, todo_id: Annotated[int, Path(gt=0)]) -> Todos:
    todo = await db.get(Todos, todo_id)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")
    return todo


TodoDep = Annotated[Todos, Depends(get_todo)]


router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoRead])
async def list_todos(db: DbSession):
    return (await db.scalars(select(Todos))).all()


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo_by_id(todo: TodoDep):
    return todo


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(db: DbSession, body: TodoRequest):
    todo = Todos(**body.model_dump())
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
