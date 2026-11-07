from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import analytics_api, pages
from core.config import BASE_DIR, settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(analytics_api.router)
app.include_router(pages.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}
