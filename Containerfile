# Todo API image. Build: podman build -t todoapp .
# Runs `alembic upgrade head`, then serves the API on port 8000.

# --- Build stage: install dependencies and the app into a virtualenv with uv ---
FROM docker.io/library/python:3.15-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so this layer is cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Then the app itself (installed into the venv, not linked to /app/src).
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# --- Runtime stage: just Python, the venv and the migrations ---
FROM docker.io/library/python:3.15-slim

RUN useradd --system --uid 1000 --no-create-home app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY alembic ./alembic

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000

# DATABASE_URL and JWT_SECRET_KEY must be provided as environment variables.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn todoapp.main:app --host 0.0.0.0 --port 8000"]
