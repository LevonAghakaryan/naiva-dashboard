from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_home_service
from app.schemas.analytics import Period
from app.schemas.home import HomeOut
from app.services.home_service import HomeService

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/page", response_model=HomeOut)
def page(
    days: int = Query(30, description="7, 30 or 90"),
    service: HomeService = Depends(get_home_service),
):
    """The dashboard summary: KPIs, follower growth, this month's finance, competitors, top posts."""
    if days not in get_args(Period):
        raise HTTPException(status_code=422, detail="days-ը պետք է լինի 7, 30 կամ 90")
    return service.page(days)
