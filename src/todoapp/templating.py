from pathlib import Path

from fastapi.templating import Jinja2Templates

# Templates and static files live inside the package so they're installed with it
# (the container image only has the installed package, not src/). Paths are resolved
# from this file, so they work whatever directory the app is started from.
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)
