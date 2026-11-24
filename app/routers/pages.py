from fastapi import APIRouter, Depends, Request
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
        "ig_configured": settings.instagram_configured,
        "ig_connected": account is not None and not account.ig_user_id.startswith("demo_"),
    }


@router.get("/")
def landing(request: Request):
    """Public landing page. Until auth exists, "Մուտք / Գրանցվել" lead straight to /home."""
    return templates.TemplateResponse(request, "landing.html", {"app_name": settings.app_name, "enter_url": "/home"})


@router.get("/home")
def home_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "home.html", _page_context(account, "home"))


@router.get("/analytics")
def analytics_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "analytics.html", _page_context(account, "analytics"))


@router.get("/finance")
def finance_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "finance.html", _page_context(account, "finance"))


@router.get("/instagram")
def instagram_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "instagram.html", _page_context(account, "instagram"))


@router.get("/competitors")
def competitors_page(request: Request, account: IgAccount | None = Depends(get_optional_ig_account)):
    return templates.TemplateResponse(request, "competitors.html", _page_context(account, "competitors"))
