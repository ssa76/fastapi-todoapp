from fastapi import APIRouter, status

router = APIRouter(tags=["root"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def check_health():
    return {"status": "Service is healthy"}
