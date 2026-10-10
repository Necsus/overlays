"""Public landing page routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

HOME_PAGE = Path(__file__).resolve().parents[1] / "static" / "home.html"
router = APIRouter()


@router.get("/", response_class=FileResponse)
def home_page() -> FileResponse:
    return FileResponse(HOME_PAGE)
