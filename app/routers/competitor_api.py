from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.dependencies import get_competitor_service
from app.schemas.competitor import CompetitorIn, CompetitorsPageOut, Period
from app.services.competitor_service import CompetitorService

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


@router.get("/page", response_model=CompetitorsPageOut)
def page(
    days: int = Query(30, description="7, 30 or 90"),
    service: CompetitorService = Depends(get_competitor_service),
):
    """You + competitors with the 6 compared metrics, and competitors' posts of the period."""
    if days not in get_args(Period):
        raise HTTPException(status_code=422, detail="days-ը պետք է լինի 7, 30 կամ 90")
    return service.page(days)


@router.post("", status_code=201)
def add(body: CompetitorIn, service: CompetitorService = Depends(get_competitor_service)):
    comp = service.add(body.username)
    return {"id": comp.id, "username": comp.username}


@router.delete("/{competitor_id}", status_code=204)
def remove(competitor_id: int, service: CompetitorService = Depends(get_competitor_service)):
    service.remove(competitor_id)
    return Response(status_code=204)
