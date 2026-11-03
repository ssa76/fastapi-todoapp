from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select

from todoapp.database import DbSession
from todoapp.models import Todos
from todoapp.routers.auth import require_admin
from todoapp.schemas import TodoRead

# Every route on this router requires an admin, including ones added later.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


async def get_any_todo(db: DbSession, todo_id: Annotated[int, Path(gt=0)]) -> Todos:
    """Load any user's todo (no owner check: admin routes only), or 404."""
    todo = await db.get(Todos, todo_id)
    if todo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Todo not found")
    return todo


AnyTodo = Annotated[Todos, Depends(get_any_todo)]


@router.get("/todos", response_model=list[TodoRead])
async def read_all(db: DbSession):
    return (await db.scalars(select(Todos))).all()


@router.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: DbSession, todo: AnyTodo):
    await db.delete(todo)
    await db.commit()
