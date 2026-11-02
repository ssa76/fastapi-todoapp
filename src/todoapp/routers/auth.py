from fastapi import APIRouter, status

from todoapp.models import Users
from todoapp.schemas import CreateUserRequest

router = APIRouter()


@router.post("/auth", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest):
    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=create_user_request.password,
        is_active=True,
    )

    return create_user_model
