r"""Nightly job: refresh tokens and sync every connected (non-demo) Instagram account.

Run once a day (Windows Task Scheduler / cron), e.g. at 04:00:
    .venv\Scripts\python.exe scripts\sync_instagram.py            # all accounts
    .venv\Scripts\python.exe scripts\sync_instagram.py --days 30  # re-read the last 30 days
Exit code 1 if any account failed (so the scheduler shows it).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.integrations.instagram_graph import InstagramAuthError, InstagramError  # noqa: E402
from app.repositories.instagram_repository import InstagramRepository  # noqa: E402
from app.services.instagram_service import InstagramService, SyncBusy  # noqa: E402
from core.database import SessionLocal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync connected Instagram accounts")
    parser.add_argument("--days", type=int, default=None, help="days to re-read (default: 3, first sync 30)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    failed = 0
    with SessionLocal() as db:
        repo = InstagramRepository(db)
        accounts = repo.real_accounts()
        if not accounts:
            print("Միացված Instagram հաշիվ չկա։")
        for acc in accounts:
            try:
                r = InstagramService(repo).sync(acc, days=args.days)
                print(f"@{r.username}: {r.days} օր, {r.posts} պոստ, {r.snapshots} նոր snapshot, "
                      f"{r.api_calls} API կանչ" + (f" | ⚠ {'; '.join(r.warnings)}" if r.warnings else ""))
            except InstagramAuthError as e:
                failed += 1
                print(f"@{acc.username}: պետք է նորից միացնել — {e}")
            except (InstagramError, SyncBusy) as e:
                failed += 1
                print(f"@{acc.username}: սխալ — {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
