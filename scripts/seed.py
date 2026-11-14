"""Demo data for @ani.travels (analytics page).

Usage (from the project folder, after db/schema.sql has been run in MySQL):
    .venv\\Scripts\\python.exe scripts\\seed.py              # fails if demo data already exists
    .venv\\Scripts\\python.exe scripts\\seed.py --reset      # deletes the demo user and re-creates it
    .venv\\Scripts\\python.exe scripts\\seed.py --analytics  # re-creates only the Instagram data
    .venv\\Scripts\\python.exe scripts\\seed.py --competitors  # re-creates only the demo competitors

Last-30-day totals are calibrated to the design (instagram-spec.md):
Followers 48,214 (+3,940 / −1,060), Reach 312K ▲12.6%, ER 7.9% ▲0.3 pp, Likes 41.2K ▲8.7%,
Views 1.21M ▲14.2%, Saves 9,600 ▼3.0%, Shares 4,700 ▲14.6%, Comments 2,480 ▲7.8%, Profile visits 18.4K ▲6.4%.
Finance (categories + transactions) is calibrated too — see scripts/seed_finance.py.
If the demo user already exists but has no finance data, only the finance part is added.
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
    AccountPeriodStats,
    AudienceOnlineHours,
    AudienceStats,
    IgAccount,
    Post,
    PostStats,
    User,
)
from core.database import SessionLocal  # noqa: E402
from scripts.seed_competitors import delete_competitors, has_competitors, seed_competitors  # noqa: E402
from scripts.seed_finance import delete_finance, has_finance, seed_finance  # noqa: E402

DEMO_EMAIL = "ani.demo@example.com"
DEMO_IG_USER_ID = "demo_ani_travels"
HISTORY_DAYS = 180  # enough for the "90 days vs previous 90" comparison
WINDOW = 30

FOLLOWERS_NOW = 48_214
# account_daily_stats column: (last-30-day total, growth vs previous 30 days)
DAILY_TARGETS = {
    "new_follows": (3_940, 0.052),
    "unfollows": (1_060, 0.041),
    "reach": (312_000, 0.126),
    "views": (1_210_000, 0.142),
    "accounts_engaged": (24_600, 0.168),  # ÷ reach → ER 7.9% vs 7.6% (▲0.3 pp)
    "likes": (41_200, 0.087),
    "comments": (2_480, 0.078),
    "saves": (9_600, -0.03),
    "shares": (4_700, 0.146),
    "reposts": (640, 0.214),
    "profile_views": (18_400, 0.064),
    "link_taps": (1_290, 0.091),
}
NON_FOLLOWER_SHARE = 0.384  # of the reach
PERIODS = (7, 30, 90)

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
    "reels": (0.16, 60_000, (1.4, 1.7), 0.020),
    "post": (0.05, 30_000, (1.1, 1.3), 0.015),
    "carousel": (0.08, 40_000, (1.3, 1.6), 0.035),
}
POST_HOURS = [10, 12, 14, 18, 19, 20, 21]

GENDER = {"F": 0.68, "M": 0.32}
AGE = {"13-17": 0.04, "18-24": 0.31, "25-34": 0.42, "35-44": 0.16, "45-54": 0.05, "55-64": 0.015, "65+": 0.005}
CITIES = {
    "Yerevan": 54, "Moscow": 9, "Los Angeles": 7, "Gyumri": 6, "Vanadzor": 4, "Sochi": 3, "Glendale": 3,
    "Kapan": 2, "Abovyan": 2, "Paris": 2, "Tbilisi": 2, "Hrazdan": 2, "Ijevan": 2, "Armavir": 2,
}
COUNTRIES = {"AM": 71, "RU": 11, "US": 9, "FR": 3, "GE": 2, "DE": 2, "UA": 1, "CA": 1}
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


def proportional(rng: random.Random, base: list[int], share: float) -> list[int]:
    """A series that is ~`share` of `base` every day and exactly `share` of it per 30-day window."""
    out = [0] * len(base)
    for idx in windows(len(base)):
        total = sum(base[i] for i in idx) * share
        for i, v in zip(idx, distribute(total, [base[i] * rng.uniform(0.9, 1.1) for i in idx])):
            out[i] = v
    return out


def followers_series(new: list[int], unf: list[int]) -> list[int]:
    """End-of-day followers, counted back from today: f[i-1] = f[i] − new[i] + unfollows[i]."""
    n = len(new)
    followers = [0] * n
    followers[-1] = FOLLOWERS_NOW
    for i in range(n - 1, 0, -1):
        followers[i - 1] = followers[i] - new[i] + unf[i]
    return followers


def build_posts(rng: random.Random, days: list[date], followers: list[int]) -> list[dict]:
    posts: list[dict] = []
    for i, d in enumerate(days):
        scale = followers[i] / FOLLOWERS_NOW
        candidates = [t for t, (p, *_rest) in POST_PROFILES.items() if rng.random() < p]
        candidates += ["story"] * rng.choice([0, 0, 1, 2])
        for t in candidates:
            if t == "story":
                reach = 2_500 * rng.lognormvariate(0, 0.3) * scale
                views = reach * rng.uniform(1.05, 1.25)
                likes, comments, saves = reach * rng.uniform(0.01, 0.03), 0, 0
                shares, reposts, follows = reach * 0.003, 0, reach * 0.0005
            else:
                _, base, (vlo, vhi), save_rate = POST_PROFILES[t]
                reach = base * rng.lognormvariate(0, 0.45) * scale
                views = reach * rng.uniform(vlo, vhi)
                likes = reach * rng.uniform(0.04, 0.09)
                comments = likes * rng.uniform(0.03, 0.08)
                saves = reach * save_rate * rng.uniform(0.6, 1.4)
                shares = reach * rng.uniform(0.005, 0.02)
                reposts = shares * rng.uniform(0.08, 0.2)
                follows = reach * rng.uniform(0.002, 0.006)
            posts.append({
                "type": t,
                "posted_at": datetime.combine(d, time(rng.choice(POST_HOURS), rng.randrange(0, 60))),
                "views": round(views), "reach": round(reach), "likes": round(likes),
                "comments": round(comments), "saves": round(saves), "shares": round(shares),
                "reposts": round(reposts), "follows": round(follows),
            })
    return posts


def delete_analytics(db: Session, acc_ids) -> None:
    """Instagram data of the given accounts (a select of ids); the accounts themselves stay."""
    post_ids = select(Post.id).where(Post.ig_account_id.in_(acc_ids))
    db.execute(delete(PostStats).where(PostStats.post_id.in_(post_ids)))
    for model in (Post, AccountDailyStats, AccountPeriodStats, AudienceStats, AudienceOnlineHours):
        db.execute(delete(model).where(model.ig_account_id.in_(acc_ids)))
    db.flush()


def delete_demo(db: Session) -> bool:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return False
    delete_finance(db, user.id)
    delete_competitors(db, user.id)
    delete_analytics(db, select(IgAccount.id).where(IgAccount.user_id == user.id))
    db.execute(delete(IgAccount).where(IgAccount.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.flush()
    return True


def seed(db: Session, today: date | None = None, rng_seed: int = 42) -> IgAccount:
    today = today or date.today()
    user = User(email=DEMO_EMAIL, password_hash="!demo-no-login", name="Անի Հակոբյան")
    acc = IgAccount(user=user, ig_user_id=DEMO_IG_USER_ID, username="ani.travels")
    acc.set_access_token("demo-token-not-real")
    db.add(user)
    seed_analytics(db, acc, today, rng_seed)
    seed_finance(db, user, today)
    db.flush()
    seed_competitors(db, user, today)
    return acc


def seed_analytics(db: Session, acc: IgAccount, today: date | None = None, rng_seed: int = 42) -> None:
    rng = random.Random(rng_seed)
    today = today or date.today()
    now = datetime.now().replace(microsecond=0)
    days = [today - timedelta(days=HISTORY_DAYS - 1 - i) for i in range(HISTORY_DAYS)]
    acc.followers_count = FOLLOWERS_NOW
    acc.last_synced_at = now - timedelta(minutes=15)

    series = {k: daily_series(rng, t, g, HISTORY_DAYS) for k, (t, g) in DAILY_TARGETS.items()}
    series["non_follower_reach"] = proportional(rng, series["reach"], NON_FOLLOWER_SHARE)
    series["interactions"] = [sum(series[k][i] for k in ("likes", "comments", "saves", "shares"))
                              for i in range(HISTORY_DAYS)]
    followers = followers_series(series["new_follows"], series["unfollows"])
    for i, d in enumerate(days):
        acc.daily_stats.append(AccountDailyStats(day=d, followers=followers[i],
                                                 **{k: v[i] for k, v in series.items()}))
    db.flush()

    # Period totals of unique-account metrics, as the API would return them.
    for n in PERIODS:
        for end_idx in (HISTORY_DAYS - 1, HISTORY_DAYS - 1 - n):
            idx = range(end_idx - n + 1, end_idx + 1)
            if idx.start < 0:
                continue
            db.add(AccountPeriodStats(
                ig_account_id=acc.id, end_day=days[end_idx], days=n,
                **{k: sum(series[k][i] for i in idx) for k in ("reach", "non_follower_reach", "accounts_engaged")},
            ))

    posts = build_posts(rng, days, followers)
    acc.media_count = sum(1 for p in posts if p["type"] != "story")
    metric_keys = ("views", "reach", "likes", "comments", "saves", "shares", "reposts", "follows")
    for n, p in enumerate(posts, start=1):
        post = Post(
            ig_media_id=f"demo_{acc.id}_{n:05d}", type=p["type"], posted_at=p["posted_at"],
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
    for label, share in COUNTRIES.items():
        acc.audience_stats.append(AudienceStats(day=today, breakdown="country", label=label, value=round(FOLLOWERS_NOW * share / 100)))

    for d in range(7):
        for h in range(24):
            value = FOLLOWERS_NOW * 0.3 * WEEKDAY_FACTOR[d] * HOUR_FACTOR[h] * rng.uniform(0.98, 1.02)
            acc.online_hours.append(AudienceOnlineHours(day=d, hour=h, value=round(value)))
    db.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo analytics data for @ani.travels")
    parser.add_argument("--reset", action="store_true", help="delete existing demo data first")
    parser.add_argument("--finance", action="store_true", help="re-create only the demo user's finance data")
    parser.add_argument("--analytics", action="store_true", help="re-create only the demo Instagram data")
    parser.add_argument("--competitors", action="store_true", help="re-create only the demo competitors")
    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
            if args.analytics:
                acc = existing and db.scalar(select(IgAccount).where(IgAccount.user_id == existing.id))
                if acc is None:
                    print("Դեմո օգտատեր չկա։ Նախ՝ scripts/seed.py")
                    return 1
                delete_analytics(db, select(IgAccount.id).where(IgAccount.id == acc.id))
                db.expire(acc)
                seed_analytics(db, acc)
                db.commit()
                print(f"Instagram-ի դեմո տվյալները նորից ստեղծված են՝ @{acc.username}: "
                      f"{len(acc.daily_stats)} օր, {len(acc.posts)} փոստ/story։")
                return 0
            if args.competitors:
                if existing is None:
                    print("Դեմո օգտատեր չկա։ Նախ՝ scripts/seed.py")
                    return 1
                delete_competitors(db, existing.id)
                comps = seed_competitors(db, existing)
                db.commit()
                print(f"Մրցակիցների դեմո տվյալները նորից ստեղծված են՝ {len(comps)} հաշիվ, "
                      f"{sum(len(c.posts) for c in comps)} փոստ։")
                return 0
            if args.finance:
                if existing is None:
                    print("Դեմո օգտատեր չկա։ Նախ՝ scripts/seed.py")
                    return 1
                delete_finance(db, existing.id)
                seed_finance(db, existing)
                db.commit()
                print("Ֆինանսների դեմո տվյալները նորից ստեղծված են։")
                return 0
            if existing is not None:
                if not args.reset:
                    if not has_competitors(db, existing.id):
                        seed_competitors(db, existing)
                        db.commit()
                        print("Մրցակիցների դեմո տվյալներն ավելացված են։")
                        return 0
                    if not has_finance(db, existing.id):
                        seed_finance(db, existing)
                        db.commit()
                        print("Ֆինանսների դեմո տվյալներն ավելացված են։")
                        return 0
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
