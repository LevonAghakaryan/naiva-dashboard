"""Nightly job: one public snapshot per competitor (Instagram Business Discovery) for every user.

Needs INSTAGRAM_SYNC=true and real access tokens (after Meta App Review). Usage:
    .venv\Scripts\python.exe scripts\sync_competitors.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.models import IgAccount  # noqa: E402
from app.repositories.analytics_repository import AnalyticsRepository  # noqa: E402
from app.repositories.competitor_repository import CompetitorRepository  # noqa: E402
from app.services.competitor_service import CompetitorService  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import SessionLocal  # noqa: E402


def main() -> int:
    if not settings.instagram_sync:
        print("INSTAGRAM_SYNC=false (.env) — Instagram API-ին չենք դիմում։")
        return 0
    with SessionLocal() as db:
        # one account per user is the source of the token
        accounts = {a.user_id: a for a in db.scalars(select(IgAccount).order_by(IgAccount.id.desc()))}
        for acc in accounts.values():
            service = CompetitorService(CompetitorRepository(db), AnalyticsRepository(db), acc)
            for handle, status in service.sync_all().items():
                print(f"@{acc.username} → @{handle}: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
