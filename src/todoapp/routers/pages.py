from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from todoapp.templating import templates

# HTML pages for the browser. Kept out of the OpenAPI schema (/docs), which documents
# the JSON API only.
router = APIRouter(tags=["pages"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html")
