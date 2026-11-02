from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from todoapp.database import DbSession
from todoapp.models import Users
from todoapp.schemas import CreateUserRequest, UserRead
from todoapp.security import hash_password

router = APIRouter()


@router.post("/auth", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(db: DbSession, body: CreateUserRequest):
    user = Users(
        **body.model_dump(exclude={"password"}),
        hashed_password=hash_password(body.password),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Username or email already registered"
        ) from None
    await db.refresh(user)
    return user
