"""Demo data for @ani.travels (analytics page).

Usage (from the project folder, after db/schema.sql has been run in MySQL):
    .venv\\Scripts\\python.exe scripts\\seed.py            # fails if demo data already exists
    .venv\\Scripts\\python.exe scripts\\seed.py --reset    # deletes the demo user and re-creates it

Last-30-day totals are calibrated to the design (PROJECT.md §3):
Views 1.2M ▲14%, Reach 312K ▲12.4%, Profile views 18.4K ▲6%, Saves 9.6K ▼3%, followers 48,230 (+1,490).
Only the demo user/account is touched; nothing else in the DB is changed.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.exc import OperationalError, ProgrammingError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models import (  # noqa: E402
    AccountDailyStats,
    AudienceOnlineHours,
    AudienceStats,
    IgAccount,
    Post,
    PostStats,
    User,
)
from core.database import SessionLocal  # noqa: E402

DEMO_EMAIL = "ani.demo@example.com"
DEMO_IG_USER_ID = "demo_ani_travels"
HISTORY_DAYS = 180  # enough for the "90 days vs previous 90" comparison
WINDOW = 30

FOLLOWERS_NOW = 48_230
FOLLOWERS_GAIN_30 = 1_490
# metric: (last-30-day total, growth vs previous 30 days)
DAILY_TARGETS = {
    "views": (1_200_000, 0.14),
    "reach": (312_000, 0.124),
    "profile_views": (18_400, 0.06),
}
SAVES_TARGET = (9_600, -0.03)

CAPTIONS = [
    "Դիլիջանի անտառներում 🌲", "Սևանի մայրամուտը 🌅", "Գառնի–Գեղարդ մեկ օրում",
    "Տաթևի ճոպանուղին՝ աշնանը 🍂", "Երևանի 5 լավագույն սրճարանները ☕", "Ջերմուկ. ինչ անել 2 օրում",
    "Արենիի գինու փառատոն 🍷", "Լոռի բերդ ու Դեբեդի կիրճ", "Հաղպատ և Սանահին", "Ամբերդ՝ ամպերի մեջ ☁️",
    "Խոր Վիրապ ու Արարատը 🏔", "Գյումրիի Կումայրի թաղամասը", "Բյուջետային ուղևորություն՝ ֏30,000-ով",
    "Ինչ վերցնել սարեր 🎒", "Շաքիի ջրվեժ 💧", "Նորավանքի ճանապարհին", "Զորաց Քարեր՝ արևածագին",
    "Գյուղական խոհանոց Սյունիքում 🥘", "Մոսկվայից Երևան՝ ճամփորդության հաքեր ✈️", "Ծաղկաձոր՝ ձմռանը ⛷",
    "Վերնիսաժի գանձերը", "Կասկադից տեսարանը գիշերը ✨", "Լաստիվեր. անտառային տնակներ",
    "Գոշավանք ու Պարզ լիճ", "Ճամփորդական vlog. 3 օր Սյունիքում",
]

# type: (probability per day, base reach, views/reach range, saves rate)
POST_PROFILES = {
    "reels": (0.35, 9_000, (1.6, 2.6), 0.020),
    "post": (0.15, 4_500, (1.2, 1.4), 0.015),
    "carousel": (0.12, 5_500, (1.4, 1.7), 0.035),
}
POST_HOURS = [10, 12, 14, 18, 19, 20, 21]

GENDER = {"F": 0.68, "M": 0.32}
AGE = {"13-17": 0.04, "18-24": 0.27, "25-34": 0.41, "35-44": 0.18, "45-54": 0.07, "55-64": 0.02, "65+": 0.01}
CITIES = {
    "Yerevan": 54, "Moscow": 9, "Los Angeles": 7, "Gyumri": 6, "Vanadzor": 4, "Sochi": 3, "Glendale": 3,
    "Kapan": 2, "Abovyan": 2, "Paris": 2, "Tbilisi": 2, "Hrazdan": 2, "Ijevan": 2, "Armavir": 2,
}
# Online heatmap shape: Tue–Thu evenings are the peak → "Երք–Հնգ, 19:00–21:00"
WEEKDAY_FACTOR = [0.85, 1.0, 1.0, 1.0, 0.82, 0.75, 0.80]
HOUR_FACTOR = [0.10, 0.06, 0.04, 0.03, 0.03, 0.05, 0.10, 0.18, 0.28, 0.35, 0.40, 0.45,
               0.55, 0.60, 0.55, 0.50, 0.55, 0.65, 0.80, 1.00, 0.98, 0.85, 0.70, 0.50]


def distribute(total: float, weights: list[float]) -> list[int]:
    """Split `total` into integers proportional to weights; the sum is exact."""
    total = round(total)
    s = sum(weights)
    if s == 0 or not weights:
        return [0] * len(weights)
    raw = [w / s * total for w in weights]
    ints = [math.floor(v) for v in raw]
    remainder = total - sum(ints)
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - ints[i], reverse=True)[:remainder]:
        ints[i] += 1
    return ints


def windows(n_days: int) -> list[list[int]]:
    """Day indexes (0 = oldest, n-1 = today) grouped into 30-day windows from the newest."""
    out = []
    for w in range(math.ceil(n_days / WINDOW)):
        out.append([n_days - 1 - k for k in range(w * WINDOW, min((w + 1) * WINDOW, n_days))])
    return out


def daily_series(rng: random.Random, target: int, growth: float, n_days: int) -> list[int]:
    shape = [(1 + 0.12 * math.sin(2 * math.pi * (i % 7) / 7)) * rng.uniform(0.75, 1.25) for i in range(n_days)]
    values = [0] * n_days
    for w, idx in enumerate(windows(n_days)):
        window_total = target / (1 + growth) ** w * len(idx) / WINDOW
        for i, v in zip(idx, distribute(window_total, [shape[i] for i in idx])):
            values[i] = v
    return values


def followers_series(rng: random.Random, n_days: int) -> list[int]:
    gains = [0] * n_days
    for w, idx in enumerate(windows(n_days)):
        total = FOLLOWERS_GAIN_30 / 1.1 ** w * len(idx) / WINDOW
        for i, g in zip(idx, distribute(total, [rng.uniform(0.5, 1.5) for _ in idx])):
            gains[i] = g
    followers = [0] * n_days
    followers[-1] = FOLLOWERS_NOW
    for i in range(n_days - 1, 0, -1):
        followers[i - 1] = followers[i] - gains[i]
    return followers


def build_posts(rng: random.Random, days: list[date], followers: list[int]) -> list[dict]:
    posts: list[dict] = []
    for i, d in enumerate(days):
        scale = followers[i] / FOLLOWERS_NOW
        candidates = [t for t, (p, *_rest) in POST_PROFILES.items() if rng.random() < p]
        candidates += ["story"] * rng.choice([0, 0, 1, 2, 3])
        for t in candidates:
            if t == "story":
                reach = 2_500 * rng.lognormvariate(0, 0.3) * scale
                views = reach * rng.uniform(1.05, 1.25)
                likes, comments, saves = reach * rng.uniform(0.01, 0.03), 0, 0
                shares = reach * 0.003
            else:
                _, base, (vlo, vhi), save_rate = POST_PROFILES[t]
                reach = base * rng.lognormvariate(0, 0.5) * scale
                views = reach * rng.uniform(vlo, vhi)
                likes = reach * rng.uniform(0.04, 0.09)
                comments = likes * rng.uniform(0.03, 0.08)
                saves = reach * save_rate * rng.uniform(0.6, 1.4)
                shares = reach * rng.uniform(0.005, 0.02)
            posts.append({
                "day_index": i, "type": t,
                "posted_at": datetime.combine(d, time(rng.choice(POST_HOURS), rng.randrange(0, 60))),
                "views": round(views), "reach": round(reach), "likes": round(likes),
                "comments": round(comments), "saves": saves, "shares": round(shares),
            })

    # Calibrate saves per 30-day window (by posted date, same as the service).
    target, growth = SAVES_TARGET
    for w, idx in enumerate(windows(len(days))):
        idx_set = set(idx)
        in_window = [p for p in posts if p["day_index"] in idx_set]
        if not in_window:
            continue
        total = target / (1 + growth) ** w * len(idx) / WINDOW
        for p, s in zip(in_window, distribute(total, [p["saves"] for p in in_window])):
            p["saves"] = s
    return posts


def delete_demo(db: Session) -> bool:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return False
    acc_ids = select(IgAccount.id).where(IgAccount.user_id == user.id)
    post_ids = select(Post.id).where(Post.ig_account_id.in_(acc_ids))
    db.execute(delete(PostStats).where(PostStats.post_id.in_(post_ids)))
    for model in (Post, AccountDailyStats, AudienceStats, AudienceOnlineHours):
        db.execute(delete(model).where(model.ig_account_id.in_(acc_ids)))
    db.execute(delete(IgAccount).where(IgAccount.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.flush()
    return True


def seed(db: Session, today: date | None = None, rng_seed: int = 42) -> IgAccount:
    rng = random.Random(rng_seed)
    today = today or date.today()
    now = datetime.now().replace(microsecond=0)
    days = [today - timedelta(days=HISTORY_DAYS - 1 - i) for i in range(HISTORY_DAYS)]

    user = User(email=DEMO_EMAIL, password_hash="!demo-no-login", name="Անի Հակոբյան")
    acc = IgAccount(
        user=user, ig_user_id=DEMO_IG_USER_ID, username="ani.travels",
        followers_count=FOLLOWERS_NOW, last_synced_at=now - timedelta(minutes=15),
    )
    acc.set_access_token("demo-token-not-real")

    followers = followers_series(rng, HISTORY_DAYS)
    series = {k: daily_series(rng, t, g, HISTORY_DAYS) for k, (t, g) in DAILY_TARGETS.items()}
    for i, d in enumerate(days):
        acc.daily_stats.append(AccountDailyStats(
            day=d, followers=followers[i], reach=series["reach"][i],
            views=series["views"][i], profile_views=series["profile_views"][i],
        ))

    posts = build_posts(rng, days, followers)
    acc.media_count = sum(1 for p in posts if p["type"] != "story")
    metric_keys = ("views", "reach", "likes", "comments", "saves", "shares")
    for n, p in enumerate(posts, start=1):
        post = Post(
            ig_media_id=f"demo_{n:05d}", type=p["type"], posted_at=p["posted_at"],
            caption=None if p["type"] == "story" else rng.choice(CAPTIONS),
        )
        final = {k: p[k] for k in metric_keys}
        first_capture = p["posted_at"] + timedelta(days=1)
        if first_capture < now:
            # early snapshot (~70%) + latest snapshot; only the latest one is counted
            post.stats.append(PostStats(captured_at=first_capture, **{k: round(v * 0.7) for k, v in final.items()}))
            post.stats.append(PostStats(captured_at=min(p["posted_at"] + timedelta(days=7), now), **final))
        else:
            post.stats.append(PostStats(captured_at=now, **final))
        acc.posts.append(post)

    for label, share in GENDER.items():
        acc.audience_stats.append(AudienceStats(day=today, breakdown="gender", label=label, value=round(FOLLOWERS_NOW * share)))
    for label, share in AGE.items():
        acc.audience_stats.append(AudienceStats(day=today, breakdown="age", label=label, value=round(FOLLOWERS_NOW * share)))
    city_total = sum(CITIES.values())
    for label, share in CITIES.items():
        acc.audience_stats.append(AudienceStats(day=today, breakdown="city", label=label, value=round(FOLLOWERS_NOW * share / city_total)))

    for d in range(7):
        for h in range(24):
            value = FOLLOWERS_NOW * 0.3 * WEEKDAY_FACTOR[d] * HOUR_FACTOR[h] * rng.uniform(0.98, 1.02)
            acc.online_hours.append(AudienceOnlineHours(day=d, hour=h, value=round(value)))

    db.add(user)
    return acc


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo analytics data for @ani.travels")
    parser.add_argument("--reset", action="store_true", help="delete existing demo data first")
    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            if db.scalar(select(User.id).where(User.email == DEMO_EMAIL)) is not None:
                if not args.reset:
                    print("Դեմո տվյալներն արդեն կան։ Նորից ստեղծելու համար՝ scripts/seed.py --reset")
                    return 0
                delete_demo(db)
                print("Հին դեմո տվյալները ջնջված են։")
            acc = seed(db)
            db.commit()
            print(f"Պատրաստ է՝ @{acc.username}: {len(acc.daily_stats)} օր, {len(acc.posts)} փոստ/story։")
            return 0
    except RuntimeError as e:  # ENCRYPTION_KEY missing
        print(f"Սխալ. {e}\nՍտեղծեք բանալի և դրեք .env-ի ENCRYPTION_KEY-ում.\n"
              '  .venv\\Scripts\\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
    except OperationalError as e:
        print(f"Չհաջողվեց միանալ MySQL-ին։ Ստուգեք .env-ի DB_* տվյալները և որ բազան ստեղծված է։\n{e.orig}")
    except ProgrammingError as e:
        print(f"Աղյուսակները չեն գտնվել։ Նախ գործարկեք db/schema.sql-ը MySQL-ում։\n{e.orig}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
