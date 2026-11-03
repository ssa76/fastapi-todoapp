from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from todoapp.config import settings
from todoapp.database import DbSession
from todoapp.models import Users
from todoapp.schemas import CreateUserRequest, Token, UserRead
from todoapp.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Tells FastAPI (and the /docs Authorize button) where clients get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Users | None:
    """Return the user if the username and password match, otherwise None."""
    user = await db.scalar(select(Users).where(Users.username == username))
    # Always run bcrypt, even for unknown users, so timing doesn't reveal which exist.
    hashed = user.hashed_password if user else None
    if not await verify_password(password, hashed):
        return None
    return user


def create_access_token(user: Users) -> str:
    claims = {
        "sub": str(user.id),  # the id never changes, unlike the username
        "username": user.username,
        "role": user.role,
        "exp": datetime.now(UTC) + settings.access_token_expire,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> Users:
    """Resolve the bearer token to an active user, or respond 401."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # never trust the token's own "alg"
            options={"require": ["exp", "sub"]},
        )
        user_id = int(claims["sub"])
    except jwt.InvalidTokenError, ValueError:  # bad signature, expired, malformed, ...
        raise unauthorized from None

    user = await db.get(Users, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[Users, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> Users:
    """Allow only admins: 401 without a valid token, 403 for logged-in non-admins."""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


AdminUser = Annotated[Users, Depends(require_admin)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(db: DbSession, body: CreateUserRequest):
    user = Users(
        **body.model_dump(exclude={"password"}),
        role="user",  # never taken from the request
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


@router.post("/token", response_model=Token)
async def login_for_access_token(db: DbSession, form_data: form_data_dep):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user))
