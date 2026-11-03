from fastapi import APIRouter, HTTPException, status

from todoapp.database import DbSession
from todoapp.routers.auth import CurrentUser
from todoapp.schemas import ChangePasswordRequest, UserRead
from todoapp.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_user(user: CurrentUser):
    """Return the logged-in user's details (never the password hash)."""
    return user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(db: DbSession, user: CurrentUser, body: ChangePasswordRequest):
    """Change the logged-in user's password; the current password must be confirmed."""
    # Re-checking the current password stops someone using a stolen or unattended
    # session (a valid token) from locking the real owner out.
    if not await verify_password(body.current_password, user.hashed_password):
        # 400, not 401: the user *is* logged in, so clients shouldn't treat this as
        # "token invalid, log in again".
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

    # `user` was loaded with this request's session (FastAPI shares one `db` per request),
    # so changing it and committing saves it.
    user.hashed_password = await hash_password(body.new_password)
    await db.commit()
