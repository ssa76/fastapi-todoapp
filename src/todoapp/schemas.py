from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, model_validator

from .security import MAX_PASSWORD_BYTES


def _fits_bcrypt(v: str) -> str:
    if len(v.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return v


# Rules for any new password (sign-up or change): 8 chars minimum, bcrypt's 72-byte maximum.
NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_fits_bcrypt)]


class Token(BaseModel):
    """OAuth2 token response, as expected by OAuth2 clients and the /docs Authorize button."""

    access_token: str
    token_type: str = "bearer"


class CreateUserRequest(BaseModel):
    """Body for creating a user."""

    username: str = Field(min_length=3)
    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    password: NewPassword
    # No `role`: clients must not choose their own role. New users are always "user".


class ChangePasswordRequest(BaseModel):
    """Body for changing the current user's password."""

    current_password: str
    new_password: NewPassword

    @model_validator(mode="after")
    def new_differs_from_current(self) -> ChangePasswordRequest:
        if self.new_password == self.current_password:
            raise ValueError("new password must be different from the current password")
        return self


class UserRead(BaseModel):
    """A user as returned by the API (never includes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool


class TodoRequest(BaseModel):
    """Body for creating or replacing a todo."""

    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(ge=1, le=5)
    complete: bool = False


class TodoRead(BaseModel):
    """A todo as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: int
    complete: bool
