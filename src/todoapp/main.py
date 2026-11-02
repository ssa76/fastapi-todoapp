import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import models
from .database import engine
from .routers import auth, todos


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables once on startup, not as an import side effect.
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Close pooled connections on shutdown.
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(todos.router)


def run() -> None:
    """Start the dev server: `uv run todoapp`."""
    import uvicorn

    uvicorn.run(
        "todoapp.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)],
    )


if __name__ == "__main__":
    run()
