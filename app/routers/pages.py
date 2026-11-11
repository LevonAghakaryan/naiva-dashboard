from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_optional_ig_account
from app.models import IgAccount
from core.config import BASE_DIR, settings

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def asset(path: str) -> str:
    """/static/<path>?v=<mtime>: a changed file gets a new URL, so browsers never use a stale copy."""
    try:
        version = int((BASE_DIR / "static" / path).stat().st_mtime)
    except OSError:
        version = 0
    return f"/static/{path}?v={version}"


templates.env.globals["asset"] = asset


def _page_context(account: IgAccount | None, active: str) -> dict:
    return {
        "app_name": settings.app_name,
        "active": active,
        "account": account,
        "user_name": account.user.name if account else None,
    }


@router.get("/")
def home():
    # Only the analytics page exists so far.
    return RedirectResponse("/analytics")


@router.get("/analytics")
def analytics_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "analytics.html", _page_context(account, "analytics"))


@router.get("/finance")
def finance_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "finance.html", _page_context(account, "finance"))
