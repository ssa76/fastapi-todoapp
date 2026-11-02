from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from todoapp.database import DbSession
from todoapp.models import Users
from todoapp.schemas import CreateUserRequest, UserRead
from todoapp.security import hash_password, verify_password

router = APIRouter()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Users | None:
    """Return the user if the username and password match, otherwise None."""
    stmt = select(Users).where(Users.username == username)
    user = await db.scalar(stmt)
    # Always run bcrypt, even for unknown users, so timing doesn't reveal which exist.
    hashed = user.hashed_password if user else None
    if not await verify_password(password, hashed):
        return None
    return user


@router.post("/auth", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(db: DbSession, body: CreateUserRequest):
    user = Users(
        **body.model_dump(exclude={"password"}),
        hashed_password=await hash_password(body.password),
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


form_data_dep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/token")
async def login_for_access_token(db: DbSession, form_data: form_data_dep):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "Successful Authentication"
