# Todo API

A small, fully async REST API for personal todo lists, built with **FastAPI**, **SQLAlchemy 2 (async)** and **PostgreSQL**.

- Users register and log in with **OAuth2 password flow + JWT** bearer tokens.
- Each user sees and edits **only their own todos**.
- **Admins** can list and delete any todo.
- The database schema is managed with **Alembic** migrations.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth` (register), `POST /auth/token` (log in, returns a JWT) |
| Todos | `GET /todos`, `POST /todos`, `GET/PUT/DELETE /todos/{id}`: own todos only |
| Users | `GET /users/me`, `PUT /users/me/password` |
| Admin | `GET /admin/todos`, `DELETE /admin/todos/{id}`: admins only |

Interactive API docs: <http://localhost:8000/docs> (use **Authorize** to log in).

## Tech stack

Python 3.15 · FastAPI · SQLAlchemy 2 (asyncio) + asyncpg · Alembic · PyJWT · bcrypt · pydantic-settings · uv · ruff · Podman

## Project layout

```
src/todoapp/
  main.py         app factory, routers, `uv run todoapp` entry point
  config.py       settings from environment / .env
  database.py     async engine, session dependency, declarative Base
  models.py       SQLAlchemy models (Users, Todos)
  schemas.py      Pydantic request/response models
  security.py     bcrypt password hashing
  templating.py   Jinja2 setup and the static_url() helper
  routers/        auth, todos, users, admin (JSON API); pages (HTML)
  templates/      Jinja2 pages: layout.html, partials/, one file per page
  static/         css/ and js/ (our own), vendor/ (Bootstrap, jQuery)
alembic/          migration environment and versions/
alembic.ini       Alembic configuration (no database URL in it)
tests/unit/       fast tests, no database
tests/integration/  API tests against a throwaway PostgreSQL (Testcontainers)
Containerfile     app image
compose.postgres.yaml   PostgreSQL for local development
compose.app.yaml        the app as a container (used with compose.postgres.yaml)
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python 3.15 for you if needed)
- [Podman](https://podman.io/) with `podman compose` (on macOS: a running `podman machine`)

## Configuration

Settings are read from environment variables or a local `.env` file (never committed).

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste as JWT_SECRET_KEY in .env
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | n/a | e.g. `postgresql+asyncpg://todo:todo@localhost:5432/todoapp` |
| `JWT_SECRET_KEY` | yes | n/a | Signs access tokens. Keep secret; changing it logs everyone out. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `20` | Token lifetime |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_PORT` | no | `todoapp` / `todo` / `todo` / `5432` | Lab database container |
| `APP_PORT` | no | `8000` | Host port for the app container |

## Run locally

```bash
# 1. Start PostgreSQL (wait until the status shows "healthy")
podman compose -f compose.postgres.yaml up -d
podman compose -f compose.postgres.yaml ps

# 2. Install dependencies (including dev tools)
uv sync

# 3. Create / update the database schema
uv run alembic upgrade head

# 4. Start the API with auto-reload
uv run todoapp
```

Open <http://localhost:8000/> for the web pages, or <http://localhost:8000/docs> for the API.

**The app does not create tables itself.** Run `alembic upgrade head` on every new database, and after pulling new migrations.

### Try it from the command line

```bash
# Register
curl -X POST localhost:8000/auth -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","first_name":"Alice","last_name":"Smith","password":"s3cretpass"}'

# Log in and keep the token
TOKEN=$(curl -s -X POST localhost:8000/auth/token -d 'username=alice&password=s3cretpass' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

# Create and list todos
curl -X POST localhost:8000/todos -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Buy milk","description":"2 litres","priority":2}'
curl localhost:8000/todos -H "Authorization: Bearer $TOKEN"
```

### Make a user an admin

New users always get the `user` role, and there's deliberately no API to change it:

```bash
podman exec todoapp-postgres_postgres_1 \
  psql -U todo -d todoapp -c "update users set role = 'admin' where username = 'alice'"
```

### Stop / reset the database

```bash
podman compose -f compose.postgres.yaml down      # stop, keep data
podman compose -f compose.postgres.yaml down -v   # stop and delete all data
```

## Web pages

Server-rendered with Jinja2 and Bootstrap 4. They call the same JSON API from
`static/js/base.js`.

| URL | Page |
|---|---|
| `/` | redirects to `/todos-page` |
| `/login`, `/register` | sign in / sign up (redirect to `/todos-page` if already logged in) |
| `/todos-page` | your todos |
| `/add-todos-page` | new todo |
| `/edit-todos-page/{id}` | edit or delete a todo |

- **Login:** after `POST /auth/token`, `base.js` stores the token in the `access_token`
  cookie. Pages read it from there; API calls send it as `Authorization: Bearer`. A page
  without a valid token redirects to `/login`, and an API call that gets 401 logs out.
- **Page URLs never start with `/auth` or `/todos`,** so they can't collide with API routes
  such as `/todos/{todo_id}`.
- **Static files:** link them with `{{ static_url('css/base.css') }}` instead of
  `url_for('static', ...)`. It adds a content hash (`?v=...`), so browsers fetch changed
  files at once, and fails on a missing file instead of a silent 404.
- **Third-party files** live in `static/vendor/<name>-<version>/`: Bootstrap 4.6.2 (the
  bundle includes Popper) and jQuery 3.7.1 slim. To upgrade, `npm pack <name>@<version>`
  into a temporary folder, copy the files from its `dist/` into a new versioned folder,
  update `templates/layout.html` and delete the old folder.

## Run in a container

The app container runs `alembic upgrade head` on start, then serves the API on port 8000. It needs `JWT_SECRET_KEY` in `.env`; the database URL is set by `compose.app.yaml`.

```bash
# Build and start PostgreSQL + the app
podman compose -f compose.postgres.yaml -f compose.app.yaml up -d --build

# Follow the app's logs (migrations, then "Uvicorn running on ...")
podman compose -f compose.postgres.yaml -f compose.app.yaml logs -f app

# Stop everything (add -v to also delete the database)
podman compose -f compose.postgres.yaml -f compose.app.yaml down
```

The containerised app uses the same database as local development. Stop a locally running `uv run todoapp` first, or pick another host port with `APP_PORT=8001`.

### Build and run the image on its own

```bash
podman build -t todoapp .
podman run --rm -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL='postgresql+asyncpg://todo:todo@host.containers.internal:5432/todoapp' \
  -e JWT_SECRET_KEY='<your key>' \
  todoapp
```

`host.containers.internal` reaches PostgreSQL published on the host. The image runs as a non-root user, and `.env` is excluded from the build (`.containerignore`).

## Database migrations (Alembic)

### How it's set up

- **The database URL comes from the app settings** (`DATABASE_URL` / `.env`), not from `alembic.ini`, so credentials never end up in the repository and the app and migrations always use the same database (`alembic/env.py`).
- **`env.py` uses the async engine** (asyncpg), the same driver as the app.
- **`target_metadata = Base.metadata`**, so `--autogenerate` compares `models.py` with the database.
- **New migration files are fixed and formatted with ruff automatically** (post-write hooks in `alembic.ini`).

### Everyday commands

```bash
uv run alembic upgrade head          # apply all pending migrations
uv run alembic current               # revision the database is at
uv run alembic history --verbose     # all migrations, oldest last
uv run alembic downgrade -1          # undo the most recent migration
uv run alembic check                 # do the models and the database differ?
uv run alembic upgrade head --sql    # print the SQL without touching the database
```

To target a different database for one command, override the URL:

```bash
DATABASE_URL=postgresql+asyncpg://todo:todo@localhost:5432/todoapp_scratch uv run alembic upgrade head
```

### Changing the schema

1. Edit `src/todoapp/models.py`, e.g. add `phone_number: Mapped[str | None]`.
2. Make sure your database is up to date: `uv run alembic upgrade head`.
3. Generate a migration from the difference:
   ```bash
   uv run alembic revision --autogenerate -m "add phone number to users"
   ```
4. **Review the new file in `alembic/versions/`.** Autogenerate can't detect renames (it sees a drop plus an add) and needs help with data changes. Check that `downgrade()` reverses `upgrade()`.
5. Apply and verify:
   ```bash
   uv run alembic upgrade head
   uv run alembic check                     # "No new upgrade operations detected."
   uv run alembic downgrade -1 && uv run alembic upgrade head   # round trip
   ```
6. Commit the migration together with the model change.

### Rules of thumb

- **Generate migrations against a database that is at `head`.** Autogenerate writes the *difference*, so a database with hand-made or out-of-date tables produces wrong migrations.
- **Never edit a migration that has been applied elsewhere.** Add a new one instead.
- **Making an existing column required:** add it as nullable, fill existing rows (`op.execute("UPDATE ...")`), then `op.alter_column(..., nullable=False)`.
- **To test the full chain from scratch,** use a throwaway database:
  ```bash
  podman exec todoapp-postgres_postgres_1 createdb -U todo todoapp_scratch
  DATABASE_URL=postgresql+asyncpg://todo:todo@localhost:5432/todoapp_scratch uv run alembic upgrade head
  podman exec todoapp-postgres_postgres_1 dropdb -U todo todoapp_scratch
  ```
- **A database whose tables already match the models but has no Alembic history:** mark it as up to date without running anything, with `uv run alembic stamp head`.

## Development

```bash
uv run ruff check --fix   # lint (and fix what's safe)
uv run ruff format        # format
```

### Tests

```bash
uv run pytest                       # everything (starts PostgreSQL on Podman)
uv run pytest -m "not integration"  # only the fast tests, no Podman needed
```

Integration tests (everything in `tests/integration/`) use
[Testcontainers](https://testcontainers.com/) to start a `postgres:18` container on Podman
once per run. They build the schema with `alembic upgrade head`, so the migrations get tested too, and
call the API through `httpx.AsyncClient`. They don't need your `.env` or the compose
database.

- **Podman only:** the tests look up Podman's API socket themselves (`podman machine` on
  macOS, `podman.socket` on Linux) and point Testcontainers at it. They also turn off Ryuk
  (Testcontainers' cleanup container); the test container is still removed when the run
  ends. If Podman isn't running, the integration tests fail with a hint on how to start it.
- **Isolation:** each test runs inside a transaction that is rolled back afterwards, and the
  app's own commits become savepoints within it. Every test starts with empty tables.
- **Fixtures** (`tests/integration/conftest.py`): `client`, `db_session`, `make_user`,
  `make_todo`, `user`, `admin`, `auth_headers(user)`, `password`.
