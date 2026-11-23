r"""Local testing without OAuth: uses INSTAGRAM_ACCOUNT_ID + INSTAGRAM_ACCESS_TOKEN from .env.

    .venv\Scripts\python.exe scripts\instagram_local.py            # read-only check, DB is not touched
    .venv\Scripts\python.exe scripts\instagram_local.py --connect  # save the account (token encrypted) to the DB
Then load everything the API keeps (90 days):  scripts\sync_instagram.py --days 90
The token is never printed.
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.integrations.instagram_graph import (  # noqa: E402
    InstagramClient,
    InstagramError,
    metric_values,
    utcnow,
)
from app.services.instagram_service import DAILY_METRICS, MEDIA_METRICS  # noqa: E402
from core.config import settings  # noqa: E402


def check() -> int:
    client = InstagramClient(settings.instagram_access_token, settings.instagram_account_id)
    ig = settings.instagram_account_id
    try:
        p = client.profile()
    except InstagramError as e:
        print(f"✗ Պրոֆիլ. {e}")
        return 1
    print(f"✓ Պրոֆիլ. @{p.username} · {p.followers} հետևորդ · {p.media_count} պոստ")

    failed = 0

    def attempt(title: str, run) -> None:
        nonlocal failed
        try:
            print(f"✓ {title}. {run()}")
        except InstagramError as e:
            failed += 1
            print(f"✗ {title}. {e}")

    media = []

    def load_media() -> str:
        media.extend(client.media(settings.instagram_media_limit))
        return f"{len(media)} հատ" + (f", վերջինը՝ {media[0].posted_at:%Y-%m-%d} ({media[0].type})" if media else "")

    attempt("Մեդիա", load_media)
    attempt("Stories", lambda: f"{len(client.stories())} ակտիվ")

    until = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    span = {"since": f"{until - timedelta(days=28):%Y-%m-%d}", "until": f"{until:%Y-%m-%d}"}
    for metric in DAILY_METRICS:
        attempt(f"Հաշվի insights (28 օր), {metric}", lambda m=metric: metric_values(client.insights(
            ig, [m], period="day", metric_type="total_value", **span)).get(m, "տվյալ չկա"))
    attempt("Follow/unfollow", lambda: client.insights(
        ig, ["follows_and_unfollows"], period="day", metric_type="total_value",
        breakdown="follow_type", **span).get("data") and "կա" or "տվյալ չկա (100-ից քիչ հետևորդ)")
    attempt("Լսարան (երկիր)", lambda: client.insights(
        ig, ["follower_demographics"], period="lifetime", metric_type="total_value",
        breakdown="country").get("data") and "կա" or "տվյալ չկա (100-ից քիչ հետևորդ)")
    attempt("Online ժամեր", lambda: "կա" if client.online_followers() else "տվյալ չկա (100-ից քիչ հետևորդ)")
    if media:
        m = media[0]
        for metric in MEDIA_METRICS[m.product_type]:
            attempt(f"Վերջին պոստի insights, {metric}", lambda x=metric: metric_values(
                client.insights(m.ig_media_id, [x])).get(x, "տվյալ չկա"))
    print(f"\n{client.calls} API կանչ, {failed} անհասանելի։ DB-ում ոչինչ չի գրվել։")
    return 0


def connect() -> int:
    from app.repositories.instagram_repository import InstagramRepository
    from app.services.instagram_service import InstagramService
    from core.database import SessionLocal

    with SessionLocal() as db:
        try:
            acc = InstagramService(InstagramRepository(db)).connect_token(
                settings.instagram_access_token, settings.instagram_account_id)
        except InstagramError as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ @{acc.username}-ը միացված է (account {acc.id})։ Հիմա՝ scripts\\sync_instagram.py --days 90")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Armenian text on any Windows console
    parser = argparse.ArgumentParser(description="Instagram local check / connect with a ready token")
    parser.add_argument("--connect", action="store_true", help="save the account to the DB")
    args = parser.parse_args()
    if not (settings.instagram_account_id and settings.instagram_access_token):
        print("✗ .env-ում լրացրեք INSTAGRAM_ACCOUNT_ID-ը և INSTAGRAM_ACCESS_TOKEN-ը։")
        return 1
    return connect() if args.connect else check()


if __name__ == "__main__":
    sys.exit(main())
