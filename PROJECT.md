# Creatorly — PROJECT.md

> Նոր սեսիայում ասեք՝ «կարդա PROJECT.md-ն ու շարունակենք»։ Այս ֆայլը նախագծի «հիշողությունն» է։
> Վերջին թարմացում՝ 2026-11-14

---

## 0. Աշխատանքի կանոններ (ԿԱՐԵՎՈՐ)
- Նախագծի թղթապանակը՝ `C:\Users\USER\Desktop\naiva-dashboard` (բացված է PyCharm-ում)
- **Համակարգում ոչինչ չփոխել։** Ամեն ինչ տեղադրվում է միայն `.venv`-ի մեջ.
  `.venv\Scripts\python.exe -m pip install --no-cache-dir ...`
  Եթե terminal-ում տողի սկզբում `(.venv)` է, `pip install`-ը նույնպես գնում է `.venv`։
- `.venv`՝ Python 3.12.4
- MySQL-ը տեղադրված է օգտատիրոջ մոտ։ **Չստուգել, չփոխել առանց թույլտվության**։ Բազան և աղյուսակները ստեղծելու համար նախ հարցնել։
- Այս թղթապանակն ունի իր սեփական git repo-ն (`main` → GitHub `LevonAghakaryan/naiva-dashboard`)։ `C:\Users\USER`-ի մեծ repo-ում **commit չանել**։ `.env`-ը երբեք git չի գնում։
- Աշխատում ենք **մաս-մաս**։ Ամեն քայլից առաջ պատմել, թե ինչ ենք անելու, ու սպասել հաստատման։

---

## 1. Ինչ ենք սարքում
SaaS dashboard Instagram բլոգերների համար (հիմնականում հայաստանյան)։ Ինտերֆեյսը հայերեն է։
**Creatorly** անունը ժամանակավոր է։

6 բաժին.
1. **Գլխավոր** — KPI-ներ, հետևորդների աճ, AI-ի օրվա ամփոփում, լավագույն փոստեր, նոր նամակներ
2. **Վիճակագրություն** — Posts/Reels/Stories, reach, լսարան, ակտիվ ժամեր, փոստերի աղյուսակ
3. **Նամակներ ու բոտեր** — inbox (3 սյունակ, AI-ի պատասխանի առաջարկ) + բոտերի կանոններ
4. **Ֆինանսներ** — մնացորդ/եկամուտ/ծախս, գործարքներ, օրացույց, սպասվողներ, գրաֆիկներ (v2, `finance-spec.md`)
5. **Մրցակիցներ** — միայն հրապարակային տվյալներ, համեմատություն, աճ, լավագույն փոստեր
6. **AI օգնական** — չատ՝ բլոգերի բոլոր տվյալների հիման վրա

---

## 2. Պատրաստի նյութեր
| Ինչ | Որտեղ |
|---|---|
| Էջերի դիզայն (canvas, 6 էջ + Sidebar) | https://claude.ai/artifact/PtSEd2C2aAyoYSyHV3VDCN |
| Էջերի նկարներ (PNG) | `C:\Users\USER\Downloads\1. Գլխավոր@1x.png` … `6. AI օգնական@1x.png` |
| Բազայի ուղեցույց | https://claude.ai/artifact/YCksVXZF62xhfnSngzf186 |
| ER դիագրամ | `C:\Users\USER\Downloads\creatorly_mysql_erd.html` |
| Ծախսերի վերլուծություն (սլայդներ) | https://claude.ai/artifact/QFmGtm4KP4o6uWPbTndUYD |
| MySQL սխեմա (v1) | `C:\Users\USER\Downloads\schema.sql` (19 աղյուսակ) |

---

## 3. Էջերի դիզայնը (ինչ կա ամեն էջում)
Բոլոր էջերում ձախ sidebar է՝ լոգո, 6 բաժին (Նամակների մոտ badge «12»), «Կարգավորումներ» և օգտատիրոջ քարտ («Անի Հակոբյան · @ani.travels · 48.2K»)։

**1. Գլխավոր** — «Բարև, Անի»։ Կա որոնում, «Վերջին 30 օր» ընտրիչ և «Արտահանել» կոճակ։
- 4 KPI՝ Հետևորդներ 48,230 (▲3.2%), Reach 312K (▲12.4%), Engagement 5.8% (▼0.4%), Եկամուտ ֏1,240,000 (▲18%)։ Յուրաքանչյուրի տակ գրված է նախորդ շրջանի արժեքը։
- Հետևորդների աճի line գրաֆիկ (+1,490)
- AI ամփոփում (3 կետ) և «Հարցնել AI-ին» կոճակ
- Լավագույն փոստերի աղյուսակ՝ Տեսակ, Views, Reach, Likes, Saves
- Նոր նամակներ («12 չպատասխանված») և «Բացել նամակները» կոճակ

**2. Instagram վիճակագրություն** — «@ani.travels · թարմացվել է 15 րոպե առաջ», ընտրիչ «Վերջին 30 օր», «Արտահանել» կոճակ։
- Ներդիրներ՝ Ընդհանուր / Reels / Posts / Stories
- 4 KPI՝ Views 1.2M (▲14%), Reach 312K (▲12.4%), Պրոֆիլի դիտումներ 18.4K (▲6%), Saves 9.6K (▼3%)
- «Reach ըստ օրերի» bar գրաֆիկ, վերջին 14 օրը։ Ամենաբարձր սյունը մուգ կապույտ է, մնացածը՝ բաց։
- Լսարան՝ Կանայք 68% / Տղամարդիկ 32% (մեկ գոտի՝ կապույտ/նարնջագույն), տարիքներ 13–17, 18–24, 25–34, 35–44, 45+ (horizontal bars)
- «Երբ է լսարանն ակտիվ»՝ heatmap 7 օր × ժամեր (09…23), badge «Լավագույն ժամը՝ Երք–Հնգ, 19:00–21:00»
- Քաղաքներ՝ Երևան 54%, Մոսկվա 9%, Լոս Անջելես 7%, Գյումրի 6%, Վանաձոր 4%
- «Բոլոր փոստերը» աղյուսակ («Դասավորված ըստ views»)՝ Փոստ, Տեսակ, Ամսաթիվ, Views, Reach, Likes, Comments, Saves, Shares, ER (կանաչ/կարմիր pill)

**3. Նամակներ ու բոտեր** — ներդիրներ՝ Նամակներ / Բոտեր (Բոտերի էջի դիզայնը դեռ չկա)։
- Ձախ սյունակ՝ որոնում, ֆիլտրեր (Բոլորը, Չկարդացված · 12, Համագործակցություն, Հարցեր), ցուցակ՝ tag-երով (Համագործակցություն, Հարց, Կարծիք, «Բոտը պատասխանել է»)
- Մեջտեղ՝ չատ, badge «Պատուհանը փակվում է 21 ժ հետո» (24 ժամվա պատուհան), «AI առաջարկ» և «Օգտագործել» կոճակ, պատասխանի դաշտ
- Աջ սյունակ՝ Մանրամասներ (Տեսակ՝ Բրենդ, Կատեգորիա, Նախկին գործարքներ), գործողություններ (Ավելացնել ֆինանսների փուլերում, Փոխանցել մենեջերին, Նշել որպես կարևոր), նշումներ

**4. Ֆինանսներ** — «Նոյեմբեր 2026», կոճակներ՝ «Սկանավորել չեկ», «Ներմուծել CSV», «+ Ավելացնել»։
- 4 KPI՝ Եկամուտ ֏1.24M, Ծախս ֏310K, Զուտ շահույթ ֏930K (մարժա 75%), Սպասվող վճարումներ ֏650K (3 գործարք)
- Եկամուտ/ծախս՝ 6 ամսվա grouped bar գրաֆիկ
- Եկամուտն ըստ աղբյուրի՝ Համագործակցություն 62%, Գովազդ (stories) 21%, Affiliate 11%, Այլ 6%
- Համագործակցությունների kanban՝ Բանակցություն → Պայմանագիր → Կատարման մեջ → Վճարված
- AI վերլուծություն (3 կետ)
- Գործարքների աղյուսակ՝ Ամսաթիվ, Նկարագրություն, Կատեգորիա, Կարգավիճակ (Վճարված / Ծախս / Սպասվող), Գումար

**5. Մրցակիցներ** (նոր դիզայն, իրականացված է՝ տես §11.3) — «Հետևում ես N հաշվի · համեմատություն 30 օրում», 7/30/90 օր, «+ Ավելացնել»։
- Մրցակիցների քարտեր (Instagram պրոֆիլի ոճով), վերջում dashed «Ավելացնել մրցակից»
- «Համեմատություն»՝ «Բոլորի հետ» (6 ցուցանիշ, միջինից շեղում, տեղ, դասակարգում, գրաֆիկներ) / «Դեմ առ դեմ»
- «Մրցակիցների լավագույն փոստերը»՝ ֆիլտր, դասավորում, էջավորում ‹ 1 2 3 ›
- Ներքևում նշում՝ «միայն հրապարակային տվյալներ, reach-ը, saves-ը, shares-ը և լսարանը Instagram-ը չի տրամադրում»

**6. AI օգնական** — ձախում զրույցների ցուցակ և «+ Նոր զրույց» կոճակ։
- Պատասխանների մեջ կան KPI մինի-քարտեր, համարակալված կետեր, «Առաջարկ» և գործողության կոճակներ
- Արագ հարցեր (chip-եր)՝ «Ինչ փոստել վաղը», «Ամփոփիր այս ամիսը» և այլն

---

## 4. Դիզայնի կանոններ
- Ոճ՝ սպիտակ քարտեր, ֆոն `#F5F7FB` (նուրբ radial gradient-ներով), accent `#2563EB`, տեքստ `#0F172A`, muted `#5B6577`
- Քարտեր՝ radius 20px, border `#E8ECF3`, փափուկ ստվեր (`--shadow`), կոճակներ ≥ 44px
- Գունավոր gradient քարտեր (2026-11-14)՝ `class="card tint tint-pink"` (blue/indigo/violet/pink/rose/amber/orange/green/teal/red). Ձախ վերևի անկյունում նուրբ գույն է։ Հիմնական կոճակը gradient է (`--grad-blue`), գրաֆիկների սյուները՝ gradient (Chart.js-ում `vGrad()`)
- Sidebar՝ gradient լոգո ✦, ակտիվ բաժինը բաց կապույտ gradient-ով, օգտատիրոջ քարտում կանաչ «online» կետ։ Հեռախոսի ներքևի nav-ն ունի 6 կետ
- Ֆոնտեր՝ Inter (լատիներեն/թվեր) + Noto Sans Armenian
- Ձախ sidebar (240px) + բովանդակություն, mobile-ում sidebar-ը բարձրանում է վերև
- Աճ՝ կանաչ pill (`#047857` / `#ECFDF5`), անկում՝ կարմիր (`#B91C1C` / `#FEF2F2`)
- Գումարներ՝ `֏`
- Թվեր՝ կրճատ ձևով (184K, 1.2M)
- Ամիսներ՝ Հունվ, Փետր, Մարտ, Ապր, Մայիս, Հունիս, Հուլիս, Օգոստ, Սեպտ, Հոկտ, Նոյ, Դեկտ
- Շաբաթվա օրեր՝ Երկ, Երք, Չրք, Հնգ, Ուրբ, Շբթ, Կիր

---

## 5. Տեխնոլոգիաներ (ՈՐՈՇՎԱԾ)
- **Backend՝ Python + FastAPI** (uvicorn, SQLAlchemy 2, PyMySQL, pydantic-settings)
- **Frontend՝ HTML + CSS + JS** (Jinja2 templates, առանց framework-ի. Ֆինանսների գրաֆիկները՝ Chart.js CDN-ից, Վիճակագրությանը՝ սեփական SVG)
- **Բազա՝ MySQL 8** (utf8mb4, InnoDB)
- Գաղտնագրում՝ `cryptography` (Fernet)՝ Instagram token-ների համար
- Hosting՝ DigitalOcean (սկզբում 1 droplet 2 vCPU/4 GB, $24), Cloudflare Free, Let's Encrypt, դոմեն `.am`

`.venv`-ում արդեն տեղադրված է (`requirements.txt`).
```
fastapi==0.162.0
uvicorn[standard]==0.54.0
sqlalchemy==2.1.8
pymysql==1.2.3
pydantic-settings==2.16.2
jinja2==3.1.6
cryptography==50.0.2
```

---

## 6. Ճարտարապետություն — շերտային
```
naiva-dashboard/
├── run.py                  # uvicorn-ով գործարկում (python run.py)
├── .env / .env.example     # DB-ի տվյալներ, ENCRYPTION_KEY (.env-ը git-ում չէ)
├── requirements.txt
├── PROJECT.md              # այս ֆայլը
├── core/
│   ├── config.py           # Settings .env-ից, BASE_DIR, sqlalchemy_url
│   ├── database.py         # engine, SessionLocal, Base
│   └── security.py         # encrypt() / decrypt() (Fernet)
├── app/
│   ├── main.py             # FastAPI app, router-ներ, /static
│   ├── dependencies.py     # get_db, get_current_ig_account, service-ների ստացում
│   ├── models/             # SQLAlchemy մոդելներ (schema.sql-ի աղյուսակները)
│   ├── schemas/            # Pydantic՝ API-ի պատասխանների ձևը
│   ├── repositories/       # ՄԻԱՅՆ DB հարցումներ
│   ├── services/           # բիզնես լոգիկա (%, ER, ագրեգացիա)
│   └── routers/            # API (/api/...) + HTML էջեր
├── static/css, static/js
├── templates/              # base.html (sidebar) + էջերը
├── db/schema.sql           # սխեմայի աշխատանքային տարբերակը
└── scripts/seed.py         # դեմո տվյալներ
```
**Կանոն**. router → service → repository → DB։ Router-ը SQL չի գրում, repository-ն հաշվարկ չի անում։

---

## 7. Բազա
6 բլոկ, 23 աղյուսակ (`db/schema.sql` v1.3, աշխատանքային տարբերակը նախագծի մեջ է).
- Users: `users`, `ig_accounts`
- Վիճակագրություն: `account_daily_stats`, `posts`, `post_stats`, `audience_stats`, `audience_online_hours`
- Նամակներ: `contacts`, `conversations`, `messages`, `bot_rules`, `bot_runs`
- Ֆինանսներ: `categories`, `deals`, `transactions`
- Մրցակիցներ: `competitors`, `competitor_daily_stats`, `competitor_posts`
- AI: `ai_chats`, `ai_messages`, `ai_insights`, `ai_usage`

Կանոններ՝ գումարները միայն `DECIMAL(14,2)`, Instagram token-ները գաղտնագրված, ամեն օր snapshot։

**Սխեմայում գտնված բացթողումներ (պետք է ուղղել).**
1. ~~heatmap-ի աղյուսակ~~ → ✅ `audience_online_hours` (day 0=Երկ…6=Կիր, hour 0–23)
2. ~~AI ծախսի հաշվիչ~~ → ✅ `ai_usage`
3. `users.plan`-ը `free/pro/business` է, իսկ սակագները՝ Start/Pro/Business։ Պետք է համաձայնեցնել։
4. ~~`ai_messages.blocks`~~ → ✅ ավելացված է (JSON)
5. «Բոտեր» ներդիրի դիզայնը դեռ չկա

---

## 8. Instagram API-ի սահմանափակումներ
- Միայն Business/Creator հաշիվներ։ Insights-ի համար պետք է Meta App Review (~2–4 շաբաթ)
- Stories-ի insights-ը հասանելի է միայն 24 ժամ → պետք է ժամանակին պահել
- Account insights՝ ~90 օր, media insights՝ մինչև 2 տարի։ Որոշ ցուցանիշներ չկան <100 հետևորդ ունեցող հաշիվների համար
- Impressions/plays հանված են → օգտագործում ենք `views`
- DM՝ 24 ժամվա պատուհան։ Comment-ից՝ 1 անձնական պատասխան 7 օրվա ընթացքում։ ~200 ավտոմատ DM/ժամ մեկ հաշվից։ Պետք է «փոխանցել մարդուն» տարբերակ
- Մրցակիցներ (Business Discovery)՝ միայն հրապարակային դաշտեր, պատմություն չկա → ամեն օր snapshot
- Ֆինանսներ՝ Instagram-ը տվյալ չի տալիս → ձեռքով / CSV / չեկի սկան (AI)

---

## 9. AI (Claude API)
| Գործ | Մոդել | Մոտ. արժեք |
|---|---|---|
| Նամակի դասակարգում + պատասխանի առաջարկ, բոտ fallback | Haiku 5.5 ($0.10 / $0.50 per 1M) | $0.0002 / նամակ |
| Չեկի սկան | Haiku 5.5 | $0.0004 / չեկ |
| AI օգնական (վերլուծական հարցեր) | Sonnet 5.5 ($2 / $10 per 1M) | $0.034 / հարց |
| AI օգնական (պարզ թվային հարցեր) | Haiku 5.5 | $0.0017 / հարց |
| Գիշերային ամփոփումներ (3 հատ) | Sonnet 5.5 Batch (−50%) | $0.057 / օր |

Կանոններ՝ prompt caching, AI-ին ուղարկել ամփոփում (ոչ ամբողջ աղյուսակներ), token-ները գրանցել ամեն բլոգերի համար, լիմիտներ ըստ սակագնի։

## 10. Ծախսեր (ամսական, USD)
- 1 բլոգերի AI՝ պասիվ $1.78 · միջին $7.36 · ակտիվ $24.84
- 10 բլոգեր՝ ≈ $128 · 100 բլոգեր՝ ≈ $1,070
- Սակագնի առաջարկ (չհաստատված)՝ Start $12 · Pro $29 · Business $59

---

## 11. Մաս 1. «Instagram վիճակագրություն» էջ — ✅ կոդը պատրաստ է

**Արված է.**
- [x] Գրադարանները տեղադրված են `.venv`-ում
- [x] `requirements.txt`, `.env.example`, `.gitignore`, `run.py`
- [x] `core/config.py`, `core/database.py`, `core/security.py`
- [x] `db/schema.sql` v1.1 (22 աղյուսակ)՝ + `audience_online_hours`, + `ai_usage`, + `ai_messages.blocks` (JSON)
- [x] `app/models/` (`user.py`, `ig_account.py`, `analytics.py`, `types.py`)՝ 7 մոդել, ստուգված SQLite-ով։ Token-ը՝ `acc.set_access_token()` / `get_access_token()`։ Վերջին վիճակագրությունը՝ `post.latest_stats`
- [x] `app/schemas/analytics.py`՝ SummaryOut/KpiItem, ReachDailyOut, AudienceOut, ActiveHoursOut (grid[day][slot], 2-ժամյա slot-եր 09…21), PostsOut/PostRow (er + er_good)։ Թվերը ուղարկվում են «հում», ֆորմատավորումը՝ JS-ում
- [x] `app/repositories/analytics_repository.py`՝ `AnalyticsRepository(db)`. get_current_account, sum_daily_stats, daily_reach, post_totals, list_posts (փոստ + վերջին snapshot, max(post_stats.id)), latest_audience, online_hours։ Ամսաթվերը ներառական են։ Ստուգված SQLite-ով
- [x] `app/services/analytics_service.py`՝ նախորդ շրջանի համեմատություն, %, ER, լսարանի % և հայերեն պիտակներ (45-54/55-64/65+ → 45+), heatmap 2-ժամյա slot-եր, լավագույն ժամ/օրեր (≥90% peak)։ ER pill՝ կանաչ, եթե ER ≥ հաշվի միջին ER (ընտրված շրջանում)
- [x] `app/dependencies.py`, `app/routers/analytics_api.py`, `app/routers/pages.py` (`/` → `/analytics`), `app/main.py` (+ `/api/health`)
- [x] `templates/base.html` (sidebar, ոչ պատրաստ բաժինները՝ «Շուտով»), `templates/analytics.html`, `static/css/main.css`, `static/js/format.js` (48.2K, ֏, «15 րոպե առաջ»), `static/js/analytics.js` (ներդիրներ, ժամանակահատված, դասավորում ըստ սյունակի, CSV արտահանում)
- [x] `scripts/seed.py`՝ @ani.travels, 180 օր (որ 90 օրը համեմատվի նախորդ 90-ի հետ)։ Վերջին 30 օրը ճշգրիտ համընկնում է դիզայնին (1.2M ▲14%, 312K ▲12.4%, 18.4K ▲6%, 9.6K ▼3%)։ `--reset`՝ վերաստեղծել
- [x] Ամբողջը ստուգված է SQLite-ով + Edge screenshot (desktop/mobile)

**Մնացել է.**
- [x] MySQL 8.0.43 (localhost)՝ `creatorly` բազան ստեղծված է (22 աղյուսակ, utf8mb4), seed արված է, API-ն ստուգված է MySQL-ով (2026-11-07)։ `.env`-ը պատրաստ է (գաղտնաբառը՝ միակի չակերտներում)

**Գործարկում (MySQL).**
1. `.env.example` → `.env`, լրացնել `DB_PASSWORD` և `ENCRYPTION_KEY`
   (`.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)։ `DB_NAME=creatorly` (schema.sql-ը այդ անունով է ստեղծում)
2. Սխեմա՝ `mysql -u root -p -e "source db/schema.sql"`
3. Դեմո տվյալներ՝ `.venv\Scripts\python.exe scripts\seed.py`
4. Սերվեր՝ `.venv\Scripts\python.exe run.py` → http://127.0.0.1:8000 (API docs՝ /docs)

Seed-ի թվերը հաշվարկվում են «այսօրվա» նկատմամբ, ուստի մի քանի օր հետո ճշգրիտ դիզայնի թվերի համար՝ `seed.py --reset`։

### v2 (2026-11-11) — ըստ `C:\Users\USER\Downloads\instagram-spec.md`-ի (+ desktop/mobile նկարներ)
Էջը ամբողջությամբ վերաշարադրված է։ Հին ներդիրները (Ընդհանուր/Reels/Posts/Stories), 4 KPI-ն և Chart.js-ը հանված են։
- **Overview / Audience** ներդիրներ։ Ժամանակահատվածը (7/30/90) փոխում է ամբողջ էջը։ «Արտահանել»-ը տալիս է CSV (ցուցանիշներ + փոստեր)
- 3 hero քարտ. Followers (զուտ աճ +N, New follows/Unfollows), Reach, ER (= accounts engaged ÷ reach, delta-ն pp-ով)։ Դրանցից հետո 12 ցուցանիշ (սկզբում երևում է 6-ը)։ Ամեն քարտ կոճակ է և բացում/փակում է գրաֆիկի պանելը (`chartFor`)։ Followers-ի պանելում կան «Ընդհանուր · New follows · Unfollows» ներդիրներ, Unfollows-ի աճը կարմիր է
- Line chart-ը սեփական SVG է (`lineChart()` analytics.js-ում)՝ monotone Catmull-Rom, նախորդ շրջանի կետագիծ (7/30 օր), Max պիտակ, tooltip-ի գոտիներ (`tabindex`, aria)։ Առանցքի պիտակները, որոնք իրար վրա կընկնեին, թաքցվում են։ 90 օրում հոսքերը շաբաթական են (13 կետ)
- Posts (10 դասավորում, տիպի ֆիլտր, ER-ը կանաչ/կարմիր՝ ըստ միջինի)։ Օրացույցում օրերը ներկված են ըստ reach-ի, կետերը ցույց են տալիս տիպը, օրը սեղմելիս ֆիլտրվում է Posts-ը (չիպով)
- **Audience ներդիր** (ըստ օգտատիրոջ նկարի)՝ «Ով է քո լսարանը» (6 քառակուսի՝ Followers, հիմնական սեռ, տարիք, քաղաք + երկիր, ER, Non-followers reach), Gender & age (+ Top cities chip-եր), Top countries, Most active times (7×8, 09–23), Follower growth (կանաչ, առանց առանցքների), Օրական/Շաբաթական reach·views·follows սյունակներ։ Overview-ում մնացել են hero-ն, ցանցը, Posts-ը և օրացույցը
- Երկրները՝ `audience_stats` breakdown `country` (ISO կոդ → հայերեն անուն `COUNTRY_LABELS`-ում)
- Static ֆայլերը միանում են `asset('js/x.js')`-ով (`?v=<mtime>`), որ browser-ը հին պատճեն չօգտագործի (`app/routers/pages.py`)
- `main.css`-ից հանված են հին էջի չօգտագործվող ոճերը (kpi, table, tabs, heatmap …)
- Դասավորությունը container query-ներով է (`.ig`)՝ 6 → 3 → 2 սյուն, շարքերը միշտ լրիվ են։ Ստուգված է 1440/1000/800/600/390 լայնություններում (Edge headless)
- «?» բացատրություններ. միաժամանակ բաց է մեկը

**Բազա v1.2** (`db/migrations/2026-11-11_instagram_v2.sql`, MySQL-ում կիրառված է 2026-11-11)։ `account_daily_stats`-ին ավելացել են `new_follows, unfollows, non_follower_reach, accounts_engaged, interactions, likes, comments, saves, shares, reposts, link_taps`, `post_stats`-ին՝ `reposts, follows`։ Նոր աղյուսակ կա՝ `account_period_stats(end_day, days, reach, non_follower_reach, accounts_engaged)`։ Reach-ը և engaged-ը եզակի հաշիվներ են, ուստի ժամանակահատվածի թիվը վերցվում է այստեղից։ Եթե տող չկա, վերցվում է օրականների գումարը։
`seed.py --analytics`-ը նորից ստեղծում է միայն Instagram-ի դեմո տվյալները (ֆինանսները չի փոխում)։ Վերջին 30 օրը = spec-ի թվերը (48,214 · 312K ▲12.6% · 7.9% ▲0.3 pp · 41.2K · 1.21M …)։

**API.**
| Endpoint | Ինչ է վերադարձնում |
|---|---|
| `GET /api/analytics/page?days=30` | Ամբողջ էջը՝ hero/grid-ի հերթականություն, 17 metric (value, previous, delta, delta_unit pct/pp/abs, good, points, prev_points, gran day/week), day/week buckets, ժամանակահատվածի posts |
| `GET /api/analytics/posts?month=YYYY-MM` | Ամսվա փոստերը օրացույցի համար + `first_month` |
| `GET /api/analytics/audience` | Սեռ, տարիք, քաղաքներ (թոփ 5) |
| `GET /api/analytics/active-hours` | Heatmap 7 × 8 երկժամյա հատված (09…23) + լավագույն ժամը |

Posts-ում stories չկան։ Փոստի ER = (likes + comments + saves + shares) / reach × 100։
Մինչև auth-ը, «ընթացիկ հաշիվը» բազայի առաջին `ig_account`-ն է։
Instagram API-ին իրական միացումը (`instagram_client.py`) կանենք Meta App Review-ից հետո։ Մինչ այդ օգտագործում ենք seed տվյալներ։

---

## 11.2 Մաս 2. «Ֆինանսներ» էջ — v2 ✅ (2026-11-09)

Վերաշարադրված է ըստ `C:\Users\USER\Downloads\finance-spec.md`-ի (+ desktop/mobile նկարներ)։ v1-ի kanban-ը (deals), «Սկանավորել չեկ», «Ներմուծել CSV», AI բլոկը **հանված են** (deals աղյուսակն ու մոդելը մնում են բազայում, API/լոգիկա չկա)։

**Կանոններ (spec §3).**
- Եկամուտ/ծախս/մնացորդ = միայն ընտրված ամսվա **կատարված** (`status='paid'`, API-ում `done`) գործարքներ։ Սպասվողները ոչ մի տեղ չեն հաշվվում, միայն «Սպասվողներից հետո՝ ֏…» (= մնացորդ + ամսվա բոլոր սպասվողները) և օրացույցի դեղին կետ
- Սպասվողների ցանկը՝ ընտրված ամսվա սպասվողները։ ✓ → done (ամսաթիվը չի փոխվում), ✕ → ջնջվում է, 6 վրկ «Հետ բերել» (նույն տվյալներով նորից POST)
- Կատեգորիաները **ամեն օգտատիրոջ սեփականն են**։ Առաջին բացման ժամանակ ստեղծվում են default-ները, իսկ հին shared (`user_id NULL`) կատեգորիաների գործարքները տեղափոխվում են (Ճամփորդություն → Տրանսպորտ, անհայտ/NULL → «Այլ»)։ «Այլ եկամուտ»/«Այլ ծախս»-ը համակարգային են, չեն ջնջվում։ Ջնջելիս գործարքները գնում են «Այլ»։ Անունը եզակի է (case-insensitive, երկու տիպում էլ)
- Գումարները API-ում **նշանով int** են (եկամուտ > 0, ծախս < 0), DB-ում՝ դրական + `type`
- Տոկոսները՝ half-up կլորացում

**Ֆայլեր.** `finance_service.py` (ամբողջ լոգիկան), `finance_repository.py`, `schemas/finance.py`, `routers/finance_api.py`, `templates/finance.html`, `static/js/finance.js`, `static/css/finance.css` (նոր)։ `base.html`-ում ավելացավ հեռախոսի ներքևի նավիգացիան (<768px, բոլոր էջերում, sidebar-ը թաքնվում է)
- `scripts/seed.py --finance`՝ նորից ստեղծում է միայն դեմո օգտատիրոջ ֆինանսները (spec §12-ի տվյալները)։ MySQL-ում արված է 2026-11-09 (հին տվյալների backup՝ JSON, Claude-ի scratchpad-ում)
- Ստուգված է՝ SQLite (service սցենարներ, migration), Edge headless CDP-ով (desktop 1440 + mobile 390՝ ավելացում, Այլ օր, հաստատում, չեղարկում/հետ բերում, կատեգորիաներ, օրվա ֆիլտր, keypad), MySQL (API 200, թվերը = spec)

**API.**
| Endpoint | Ինչ է անում |
|---|---|
| `GET /api/finance/page?month=YYYY-MM` | Ամբողջ էջը՝ summary, գործարքներ (done), pending, calendar, categories (+count), monthly (6), by_category |
| `POST /api/finance/transactions` | `{type, amount>0, date, title?, category_id?, status: done/pending}` |
| `PUT /api/finance/transactions/{id}` | Խմբագրել (նույն դաշտերը, ինչ POST-ում) |
| `POST /api/finance/transactions/{id}/confirm` | pending → done |
| `DELETE /api/finance/transactions/{id}` | Ջնջել (սպասվողի չեղարկում) |
| `POST /api/finance/categories`, `DELETE /api/finance/categories/{id}` | Կատեգորիաներ |

**Խմբագրում (2026-11-09).** Գործարքների և սպասվողների ցանկում տողի վրա սեղմելիս բացվում է նույն ավելացման ձևը (desktop form / mobile sheet)՝ լրացված։ Կարելի է փոխել ամեն ինչ (տեսակ, գումար, օր, կատեգորիա, նկարագրություն, կարգավիճակ)։ Ձևում կա «Ջնջել» կոճակ, որից հետո toast-ում 6 վրկ երևում է «Հետ բերել» (նույն տվյալներով POST)։ Եթե նկարագրությունը հավասար է կատեգորիայի անվանը, ձևում այն ցույց է տրվում դատարկ։ Service-ում create-ն ու update-ը օգտագործում են միևնույն `_apply()`-ը։ Ստուգված է SQLite-ով (service + Edge headless, desktop/mobile)։ MySQL-ով դեռ չի ստուգվել։

**Մնացել է / հնարավոր քայլեր.** նախորդ ամիսներից ուշացած սպասվողների ցուցադրում։

---

## 11.3 Մաս 3. «Մրցակիցներ» էջ ✅ (2026-11-14)

Իրականացված է ըստ «Մրցակիցներ» էջի առաջադրանքի (desktop/mobile նկարներ)։ Էջը՝ `/competitors` (sidebar-ում և հեռախոսի nav-ում ակտիվ է)։

**Տվյալներ (Instagram Business Discovery, միայն հրապարակային).** Պրոֆիլից վերցնում ենք username, name, biography, website, profile_picture_url, followers_count, follows_count և media_count։ Ամեն փոստից՝ caption, like_count, comments_count, view_count, media_type/media_product_type, permalink, media_url, thumbnail_url և timestamp։ Like-երը թաքցված լինելու դեպքում `likes = NULL` է։
- **Saves, Shares, Reach-ը և լսարանը հասանելի չեն** (insights են), ուստի համեմատության 6-րդ ցուցանիշը Saves-ի փոխարեն **Views (միջին)** է, իսկ փոստերում Shares/Saves-ի փոխարեն ցույց են տրվում Views և ER։
- «Դու»-ն չափվում է նույն կերպ՝ քո փոստերի likes/comments/views-ով, որ համեմատությունը արդար լինի։
- ER = (likes + comments) / followers × 100, միջինը մեկ փոստի համար։ Posts/շաբ. = փոստեր / (օրեր / 7)։ Likes, Comments և Views-ը միջինն են մեկ փոստի համար։ Ժամանակահատվածը 7/30/90 օր է։

**Ֆունկցիոնալ.**
- Քարտեր՝ @handle, ✕, ↗ (Instagram), avatar՝ գույնի օղակով, Followers։ Քարտին սեղմելիս բացվում է «Դեմ առ դեմ»-ը (քո քարտից՝ «Բոլորի հետ») և էկրանը սահում է բաժնին։
- «Ավելացնել»-ը ներկառուցված ձև է (handle, @handle կամ հղում), առավելագույնը 10 մրցակից։ Սինք չեղած մրցակցի քարտին գրված է «Սպասում է sync-ի»։
- Համեմատություն. «Բոլորի հետ» (diverging bar, տեղ, %, բացվող դասակարգում + գրաֆիկ, «Դիտել բոլոր գրաֆիկները»՝ 6 քառակուսի) և «Դեմ առ դեմ» (ընտրիչ, ամփոփում X/6, 6 զույգ քարտ), ինչպես նաև «?» բացատրություն։
- Փոստեր. տեսակ, դասավորում (Likes / Comments / Views / ER / Վերջինը) և էջավորում՝ 5-ական։ Շատ էջերի դեպքում ցույց է տրվում «1 … 5 6 7 … 14», հեռախոսում՝ «1 … 6 … 14»։
- Responsive-ը container query-ներով է, իսկ քարտերը՝ 5 → 4 → 3 → 2 (≤1300/1000/700px)։
- «Դիտել գրաֆիկը» / «Դիտել բոլոր գրաֆիկները» կոճակները սպիտակ են՝ կապույտ եզրագծով ու տեքստով (`.ghost-btn`)։ Էջի `button`-ների ընդհանուր կանոնը `:where(.cp) button`-ն է (զրո specificity), որ կոճակների սեփական գույնը չփոխվի։

**Ֆայլեր.** `app/models/competitor.py`, `app/integrations/instagram_discovery.py` (Graph API client՝ `urllib`-ով), `competitor_repository.py`, `competitor_service.py` (+ sync/upsert), `schemas/competitor.py`, `routers/competitor_api.py`, `templates/competitors.html`, `static/css/competitors.css`, `static/js/competitors.js`, `scripts/seed_competitors.py`, `scripts/sync_competitors.py` (գիշերային job)։

**Բազա v1.3** (`db/migrations/2026-11-14_competitors.sql`, MySQL-ում կիրառված է 2026-11-14).
- `competitors` + biography, website, profile_picture_url, last_synced_at, sync_error;
- `competitor_daily_stats` + follows_count;
- `competitor_posts` + views, media_url, thumbnail_url, likes NULL. Unique-ը `(competitor_id, ig_media_id)` է, որ նույն հաշվին կարողանան հետևել տարբեր օգտատերեր։

**Կարգավորում.** `.env`-ում `INSTAGRAM_SYNC=false`-ը լռելյայն է։ Այդ դեպքում մրցակիցը պահվում է միայն handle-ով, և Instagram-ին դիմում չի լինում։ Meta App Review-ից հետո պետք է դնել `true` (`GRAPH_API_VERSION=v24.0`)։

**Դեմո.** `seed.py --competitors` (6 մրցակից, 180 օր, ~420 փոստ, @hayk.eats-ի որոշ փոստերում likes-ը թաքցված է)։

**API.**
| Endpoint | Ինչ է անում |
|---|---|
| `GET /api/competitors/page?days=30` | Մասնակիցներ (դու + մրցակիցներ, 6 ցուցանիշ, followers_delta, bio …) + ժամանակահատվածի փոստեր (ER, er_good) |
| `POST /api/competitors` | `{username}`. ստուգումներ՝ քո հաշիվը, կրկնություն, ≤10, ձևաչափ |
| `DELETE /api/competitors/{id}` | Հեռացնում է պատմության հետ միասին |

Ստուգված է MySQL-ով (API + UI), SQLite-ով (`seed --reset`-ի ճանապարհը), mock-ված Business Discovery-ով (sync, upsert, մերժում) և Edge headless-ով 375/768/1280/1440px լայնություններում (կտրվածքներ և horizontal scroll չկան)։ Ինտերակցիաներն էլ են ստուգված՝ ✕, ↗, քարտի click/Enter, էջավորում, ֆիլտրեր, ավելացում և հեռացում։

---

## 12. Հաջորդ քայլեր (ընդհանուր)
- [x] Մաս 1-ի կոդը (Վիճակագրություն)
- [x] Մաս 2՝ Ֆինանսներ (v2՝ 2026-11-09)
- [x] Մաս 3՝ Մրցակիցներ (2026-11-14)
- [ ] Մյուս էջերը՝ մեկ առ մեկ (Նամակներ ու բոտեր, AI օգնական, Գլխավոր՝ վերջում)
- [x] GitHub repo՝ https://github.com/LevonAghakaryan/naiva-dashboard (branch `main`)
- [ ] Ստեղծել Meta Developer app և պատրաստվել App Review-ին
- [ ] Ընտրել վերջնական անունը և դոմենը
- [ ] Auth + Instagram միացում + գիշերային sync

## 13. Ինչպես աշխատել Claude-ի հետ
- Մեկ հաղորդագրություն = մեկ պարզ առաջադրանք
- Մեծ փուլից հետո ասեք «թարմացրու PROJECT.md-ն», բացեք նոր սեսիա և ասեք «կարդա PROJECT.md-ն»
