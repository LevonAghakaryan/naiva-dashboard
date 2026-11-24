"""Live Instagram data (read-only) for the /instagram page. The browser calls only these endpoints;
the token stays on the server (get_instagram_credentials).

  GET /api/instagram/profile
  GET /api/instagram/media?after=<cursor>
  GET /api/instagram/media/{id}?type=FEED|REELS|STORY&carousel=0|1   → children + post insights
  GET /api/instagram/media/{id}/comments
  GET /api/instagram/insights?days=28
All accept ?refresh=1 to bypass the 5-minute cache.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.integrations.instagram_graph import InstagramAuthError, InstagramError, InstagramRateLimit
from app.services.instagram_live_service import InstagramLiveService, InstagramNotConfigured

router = APIRouter(prefix="/api/instagram", tags=["instagram-live"])
MediaId = Path(pattern=r"^\d{1,30}$")


def _run(call):
    try:
        return call(InstagramLiveService())
    except InstagramNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except InstagramAuthError as e:
        raise HTTPException(status_code=401, detail=f"Token-ը վավեր չէ կամ ժամկետն անցել է․ {e}") from e
    except InstagramRateLimit as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    except InstagramError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/profile")
def profile(refresh: bool = False):
    return _run(lambda s: s.profile(refresh))


@router.get("/media")
def media(after: str | None = Query(None, max_length=512), refresh: bool = False):
    return _run(lambda s: s.media(after, refresh))


@router.get("/media/{media_id}")
def media_detail(media_id: str = MediaId, type: str = "FEED", carousel: bool = False, refresh: bool = False):
    return _run(lambda s: s.media_detail(media_id, type.upper(), carousel, refresh))


@router.get("/media/{media_id}/comments")
def comments(media_id: str = MediaId, refresh: bool = False):
    return _run(lambda s: s.comments(media_id, refresh))


@router.get("/insights")
def insights(days: int = Query(28, ge=1, le=30), refresh: bool = False):
    return _run(lambda s: s.account_insights(days, refresh))
