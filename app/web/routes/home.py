"""Public landing page and crawler policy routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

HOME_PAGE = Path(__file__).resolve().parents[1] / "static" / "home.html"
ROBOTS_FILE = HOME_PAGE.with_name("robots.txt")
router = APIRouter()


@router.get("/", response_class=FileResponse)
def home_page() -> FileResponse:
    return FileResponse(HOME_PAGE)


@router.get("/robots.txt", response_class=FileResponse, include_in_schema=False)
def robots_txt() -> FileResponse:
    return FileResponse(ROBOTS_FILE, media_type="text/plain")
