from pydantic import BaseModel, ConfigDict, Field


class CreateUserRequest(BaseModel):
    """Body for creating a user."""

    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str


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
