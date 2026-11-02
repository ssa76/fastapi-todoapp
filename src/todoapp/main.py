import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .database import SessionLocal, engine
from .models import Todos
from .schemas import TodoRead, TodoRequest


async def get_db():
    # Closing the session rolls back any uncommitted work; errors propagate to FastAPI.
    async with SessionLocal() as db:
        yield db


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_todo(db: DbSession, todo_id: Annotated[int, Path(gt=0)]) -> Todos:
    todo = await db.get(Todos, todo_id)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")
    return todo


TodoDep = Annotated[Todos, Depends(get_todo)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables once on startup, not as an import side effect.
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Close pooled connections on shutdown.
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


# Routes are `async def`: every database call is awaited on the async session.


@app.get("/todos", response_model=list[TodoRead])
async def list_todos(db: DbSession):
    return (await db.scalars(select(Todos))).all()


@app.get("/todos/{todo_id}", response_model=TodoRead)
async def get_todo_by_id(todo: TodoDep):
    return todo


@app.post("/todos", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(db: DbSession, body: TodoRequest):
    todo = Todos(**body.model_dump())
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@app.put("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: DbSession, todo: TodoDep, body: TodoRequest):
    for field, value in body.model_dump().items():
        setattr(todo, field, value)
    await db.commit()


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: DbSession, todo: TodoDep):
    await db.delete(todo)
    await db.commit()


def run() -> None:
    """Start the dev server: `uv run todoapp`."""
    import uvicorn

    uvicorn.run(
        "todoapp.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)],
    )


if __name__ == "__main__":
    run()
