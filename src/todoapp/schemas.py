from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .security import MAX_PASSWORD_BYTES


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
    password: str = Field(min_length=8)
    # No `role`: clients must not choose their own role. New users are always "user".

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
        return v


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
