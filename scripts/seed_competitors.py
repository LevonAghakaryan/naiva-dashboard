"""Demo competitors for the demo user: 6 public accounts, 180 days of daily snapshots and posts.

Only fields Instagram Business Discovery really returns are filled (followers, follows, media count,
bio, website; per post: type, caption, permalink, likes, comments, views). @hayk.eats hides likes
on some posts (likes = NULL), as real accounts can.

Used by scripts/seed.py (`--competitors` re-creates only this part).
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Competitor, CompetitorDailyStats, CompetitorPost, User

HISTORY_DAYS = 180

# handle: (name, followers now, growth over 180 days, ER %, posts/week, comments share of likes,
#          reels views ÷ followers, (reels, carousel, post) mix, hidden-likes share, bio, website)
PROFILES = {
    "lilit.style": ("Լիլիթ Սարգսյան", 61_700, 0.07, 6.4, 3.4, 0.05, 1.7, (0.5, 0.35, 0.15), 0,
                    "Ոճ, գնումներ ու capsule wardrobe 🇦🇲 Երևան", "lilitstyle.am"),
    "mariam.daily": ("Մարիամ Ավետիսյան", 39_400, 0.09, 7.6, 2.6, 0.07, 1.3, (0.35, 0.45, 0.2), 0,
                     "Ամենօրյա կյանք, մայրություն ու խոհանոց", None),
    "narek.vlogs": ("Նարեկ Մանուկյան", 27_900, 0.15, 9.8, 1.8, 0.06, 2.6, (0.8, 0.1, 0.1), 0,
                    "Vlog-եր Հայաստանից ու աշխարհից 🎥", "youtube.com/@narekvlogs"),
    "sona.fit": ("Սոնա Գրիգորյան", 15_400, -0.02, 5.6, 4.1, 0.04, 1.1, (0.55, 0.3, 0.15), 0,
                 "Ֆիթնես մարզիչ · օնլայն ծրագրեր 💪", "sonafit.am"),
    "hayk.eats": ("Հայկ Պետրոսյան", 21_300, 0.11, 10.6, 1.5, 0.09, 2.1, (0.6, 0.3, 0.1), 0.15,
                  "Երևանի լավագույն համերը 🍔 food blogger", None),
    "armen.trips": ("Արմեն Հովհաննիսյան", 17_300, 0.04, 5.0, 2.2, 0.05, 1.2, (0.4, 0.4, 0.2), 0,
                    "Արշավներ ու ճամփորդություններ ⛰", None),
}

CAPTIONS = {
    "lilit.style": ["Աշնանային 5 կոմբինացիա", "Բյուջետային shopping", "Capsule wardrobe՝ 12 իրից",
                    "Ինչ հագնել հարսանիքի", "Second-hand գտածոներ ✨", "Գույների համադրություն",
                    "Ձմեռային վերարկուներ 2026", "Աքսեսուարների 3 կանոն"],
    "mariam.daily": ["Իմ առավոտյան ռուտինը", "Ինչ կա իմ պայուսակում", "Ինչպես եմ պլանավորում շաբաթս",
                     "Տատիկի գաթայի բաղադրատոմսը", "Մեկ օր իմ կյանքից", "Տան կազմակերպում 🧺",
                     "Կիրակնօրյա նախաճաշ"],
    "narek.vlogs": ["48 ժամ Թբիլիսիում", "Գիշերային Երևան 🌃", "Ինչքան արժե ճամփորդել Վրաստանում",
                    "Թռիչք դեպի Դուբայ", "Լոռու գյուղերում", "Q&A՝ ձեր հարցերը", "Vlog. նոր տեսախցիկ"],
    "sona.fit": ["15 րոպեանոց մարզում տանը", "Ինչ եմ ուտում մեկ օրում", "Abs challenge՝ օր 1",
                 "Սխալներ սքվատի ժամանակ", "Պրոտեինային նախաճաշ", "Ձգումներ աշխատանքից հետո"],
    "hayk.eats": ["Երևանի ամենահյութալի բուրգերը", "Խորովածի 5 լավագույն վայրը", "Շաուրմա՝ ֏1500-ով",
                  "Նոր սրճարան Կասկադի մոտ ☕", "Թոնրի լավաշ ու խաշ", "Desserts tour 🍰"],
    "armen.trips": ["Արագածի գագաթին", "Լաստիվերի արշավ", "Ինչ վերցնել արշավի", "Դիլիջան՝ 2 օրում",
                    "Ջերմուկի ջրվեժը ձմռանը", "Սյունիքի կածաններով"],
}


def has_competitors(db: Session, user_id: int) -> bool:
    return db.scalar(select(Competitor.id).where(Competitor.user_id == user_id).limit(1)) is not None


def delete_competitors(db: Session, user_id: int) -> None:
    ids = select(Competitor.id).where(Competitor.user_id == user_id)
    db.execute(delete(CompetitorPost).where(CompetitorPost.competitor_id.in_(ids)))
    db.execute(delete(CompetitorDailyStats).where(CompetitorDailyStats.competitor_id.in_(ids)))
    db.execute(delete(Competitor).where(Competitor.user_id == user_id))
    db.flush()


def seed_competitors(db: Session, user: User, today: date | None = None, rng_seed: int = 7) -> list[Competitor]:
    rng = random.Random(rng_seed)
    today = today or date.today()
    now = datetime.now().replace(microsecond=0)
    days = [today - timedelta(days=HISTORY_DAYS - 1 - i) for i in range(HISTORY_DAYS)]
    out = []
    for handle, (name, f_now, growth, er, per_week, c_share, rv, mix, hidden, bio, site) in PROFILES.items():
        comp = Competitor(user_id=user.id, username=handle, ig_user_id=f"demo_{handle}", name=name,
                          biography=bio, website=site and f"https://{site}",
                          last_synced_at=now - timedelta(hours=3))
        db.add(comp)
        f_start = f_now / (1 + growth)
        followers = []
        for i in range(HISTORY_DAYS):
            trend = f_start + (f_now - f_start) * (i / (HISTORY_DAYS - 1)) ** 1.15
            followers.append(round(trend * (1 + rng.uniform(-0.0015, 0.0015))) if i < HISTORY_DAYS - 1 else f_now)

        media_before = rng.randint(300, 900)
        follows = rng.randint(300, 1200)
        n_posts = 0
        for i, d in enumerate(days):
            for _ in range(2):  # two possible slots a day → per_week / 7 posts a day on average
                if rng.random() < per_week / 14:
                    n_posts += 1
                    kind = rng.choices(("reels", "carousel", "post"), weights=mix)[0]
                    posted = datetime.combine(d, time(rng.randint(9, 22), rng.choice((0, 15, 30, 45))))
                    if posted > now:
                        posted = now - timedelta(minutes=rng.randint(10, 120))
                    quality = rng.lognormvariate(0, 0.38)
                    kind_k = {"reels": 1.1, "carousel": 1.0, "post": 0.75}[kind]
                    likes = round(followers[i] * er / 100 / (1 + c_share) * quality * kind_k)
                    comments = round(likes * c_share * rng.uniform(0.7, 1.3))
                    view_k = rv if kind == "reels" else rv * 0.35
                    views = round(followers[i] * view_k * quality * rng.uniform(0.8, 1.2))
                    comp.posts.append(CompetitorPost(
                        ig_media_id=f"demo_{handle}_{n_posts:04d}", type=kind,
                        caption=rng.choice(CAPTIONS[handle]),
                        permalink=f"https://www.instagram.com/{'reel' if kind == 'reels' else 'p'}/demo{handle.replace('.', '')}{n_posts}/",
                        likes=None if rng.random() < hidden else likes, comments=comments,
                        views=None if rng.random() < 0.05 else views, posted_at=posted,
                    ))
            comp.daily_stats.append(CompetitorDailyStats(
                day=d, followers=followers[i], follows_count=follows + rng.randint(-3, 3),
                media_count=media_before + n_posts,
            ))
        out.append(comp)
    db.flush()
    return out
