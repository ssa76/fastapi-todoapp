import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import engine
from .routers import admin, auth, pages, root, todos, users
from .templating import STATIC_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created and changed by Alembic, not here:
    # run `uv run alembic upgrade head` before starting the app on a new database.
    yield
    # Close pooled connections on shutdown.
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fast API Todo app",
        version="1.0.0",
        description="TODO application",
        lifespan=lifespan,
    )

    # app.add_middleware(RequestLoggingMiddleware)
    # app.add_exception_handler(DomainError, domain_error_handler)

    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(todos.router)
    app.include_router(users.router)
    app.include_router(root.router)
    app.include_router(pages.router)

    # CSS, JS and images, referenced from templates as url_for('static', path=...).
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()


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
