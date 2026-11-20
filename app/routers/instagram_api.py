"""Connect Instagram (OAuth) + manual sync.

  GET  /auth/instagram/login     → redirect to instagram.com (state in an httpOnly cookie)
  GET  /auth/instagram/callback  → verify state, store the token, start the first sync in background
  GET  /api/instagram/status     → is the app configured, which account is connected, last sync
  POST /api/instagram/sync       → sync the current account now

NOTE: there is no user auth yet, so these routes act for the local owner. Before deploying
publicly they must require a logged-in user (PROJECT.md §12 «Auth»).
"""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_optional_ig_account
from app.integrations.instagram_graph import InstagramAuthError, InstagramClient, InstagramError
from app.models import IgAccount
from app.repositories.instagram_repository import DEMO_PREFIX, InstagramRepository
from app.services.instagram_service import (
    InstagramNotProfessional,
    InstagramService,
    SyncBusy,
)
from core.config import settings
from core.database import SessionLocal

log = logging.getLogger(__name__)
router = APIRouter(tags=["instagram"])

STATE_COOKIE = "ig_oauth_state"
STATE_MAX_AGE = 600  # seconds to finish the Instagram consent screen
DONE_URL = "/analytics"


def _require_configured() -> None:
    if not settings.instagram_configured:
        raise HTTPException(status_code=503, detail="Instagram-ը կարգավորված չէ (.env → INSTAGRAM_APP_ID / SECRET)")


def _back(status: str) -> RedirectResponse:
    resp = RedirectResponse(f"{DONE_URL}?ig={status}", status_code=303)
    resp.delete_cookie(STATE_COOKIE, path="/auth/instagram")
    return resp


def sync_in_background(account_id: int) -> None:
    """Own DB session: runs after the response is sent."""
    with SessionLocal() as db:
        repo = InstagramRepository(db)
        account = repo.get_account(account_id)
        if account is None:
            return
        try:
            InstagramService(repo).sync(account)
        except (InstagramError, SyncBusy) as e:
            log.warning("background sync @%s failed: %s", account.username, e)


@router.get("/auth/instagram/login", include_in_schema=False)
def login():
    _require_configured()
    state = secrets.token_urlsafe(32)
    resp = RedirectResponse(InstagramClient.authorize_url(state), status_code=303)
    resp.set_cookie(
        STATE_COOKIE, state, max_age=STATE_MAX_AGE, httponly=True, samesite="lax",
        secure=settings.instagram_redirect_uri.startswith("https://"), path="/auth/instagram",
    )
    return resp


@router.get("/auth/instagram/callback", include_in_schema=False)
def callback(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    _require_configured()
    q = request.query_params
    expected = request.cookies.get(STATE_COOKIE) or ""
    if not expected or not secrets.compare_digest(expected, q.get("state") or ""):
        return _back("state")  # CSRF / expired consent: never use this code
    if q.get("error"):
        return _back("denied")  # user pressed "Cancel"
    code = q.get("code")
    if not code:
        return _back("error")
    try:
        account = InstagramService(InstagramRepository(db)).connect(code)
    except InstagramNotProfessional:
        return _back("not_professional")
    except InstagramError as e:
        log.warning("instagram connect failed: %s", e)
        return _back("error")
    background.add_task(sync_in_background, account.id)
    return _back("connected")


@router.get("/api/instagram/status")
def status(account: IgAccount | None = Depends(get_optional_ig_account)):
    real = account is not None and not account.ig_user_id.startswith(DEMO_PREFIX)
    return {
        "configured": settings.instagram_configured,
        "connected": real,
        "username": account.username if real else None,
        "last_synced_at": account.last_synced_at.isoformat() if real and account.last_synced_at else None,
        "token_expires_at": account.token_expires_at.isoformat() + "Z" if real and account.token_expires_at else None,
    }


@router.post("/api/instagram/sync")
def sync_now(db: Session = Depends(get_db), account: IgAccount | None = Depends(get_optional_ig_account)):
    if account is None or account.ig_user_id.startswith(DEMO_PREFIX):
        raise HTTPException(status_code=404, detail="Instagram հաշիվը միացված չէ")
    repo = InstagramRepository(db)
    account = repo.get_account(account.id)  # bind to this session
    try:
        result = InstagramService(repo).sync(account)
    except SyncBusy as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except InstagramAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    except InstagramError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {
        "posts": result.posts, "days": result.days, "audience": result.audience,
        "online_hours": result.online_hours, "warnings": result.warnings,
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
    }
