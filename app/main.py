from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import analytics_api, competitor_api, finance_api, pages
from app.services.competitor_service import CompetitorInvalid, CompetitorNotFound
from app.services.finance_service import FinanceInvalid, FinanceNotFound
from core.config import BASE_DIR, settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(analytics_api.router)
app.include_router(finance_api.router)
app.include_router(competitor_api.router)
app.include_router(pages.router)


@app.exception_handler(FinanceNotFound)
@app.exception_handler(CompetitorNotFound)
def _not_found(_: Request, exc: FinanceNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FinanceInvalid)
@app.exception_handler(CompetitorInvalid)
def _invalid(_: Request, exc: FinanceInvalid):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
