import hashlib
from functools import lru_cache
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from jinja2.runtime import Context

# Templates and static files live inside the package so they're installed with it
# (the container image only has the installed package, not src/). Paths are resolved
# from this file, so they work whatever directory the app is started from.
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@lru_cache(maxsize=256)
def _content_hash(file: Path, mtime_ns: int) -> str:
    # mtime_ns is part of the cache key only: an edited file gets re-hashed, an unchanged
    # one is read once per process.
    return hashlib.sha256(file.read_bytes()).hexdigest()[:12]


def static_version(file: Path) -> str:
    """Short hash of a file's contents; changes whenever the file does."""
    return _content_hash(file, file.stat().st_mtime_ns)


@pass_context
def static_url(context: Context, path: str) -> str:
    """URL of a static file with a content version, e.g. /static/js/base.js?v=3f9a1c2b4d5e.

    Use instead of url_for('static', ...) in templates. Browsers may keep using a cached
    file for a while, but a changed file gets a new URL, so they fetch it straight away.
    A missing file raises, so a typo in a template fails loudly instead of a silent 404.
    """
    file = (STATIC_DIR / path).resolve()
    if not file.is_relative_to(STATIC_DIR.resolve()) or not file.is_file():
        raise FileNotFoundError(f"No static file {path!r} in {STATIC_DIR}")
    url = context["request"].url_for("static", path=path)
    return str(url.include_query_params(v=static_version(file)))


templates.env.globals["static_url"] = static_url
