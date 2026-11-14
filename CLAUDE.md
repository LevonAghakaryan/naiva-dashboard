# Creatorly — Claude-ի համար (կարճ)

Instagram բլոգերների dashboard. FastAPI + Jinja2 + vanilla JS/CSS + MySQL 8։ UI-ն հայերեն է, Instagram-ի տերմինները՝ անգլերեն։
Մանրամասները PROJECT.md-ում են (~40KB). **ամբողջը մի կարդա**. բաժինը գտիր `grep -n "^## " PROJECT.md`-ով և կարդա միայն այն (offset/limit)։

## Կանոններ
- Ամեն ինչ միայն `.venv`-ում (`.venv\Scripts\python.exe`)։ Համակարգում ոչինչ չփոխել։
- MySQL-ում սխեմա/տվյալներ փոխելուց առաջ հարցնել։ Commit/push՝ միայն երբ ասում են (`main` → GitHub)։
- Շերտեր՝ router → service → repository → DB։ Թվերը API-ից «հում» են, ֆորմատը JS-ում (`static/js/format.js`)։

## Ֆայլերի քարտեզ (ամեն էջ = նույն 6–7 ֆայլը)
| Էջ | Ֆայլեր |
|---|---|
| Վիճակագրություն `/analytics` | `analytics_service.py`, `analytics_repository.py`, `schemas/analytics.py`, `analytics_api.py`, `templates/analytics.html`, `static/js/analytics.js`, `static/css/analytics.css` |
| Ֆինանսներ `/finance` | `finance_*` նույն թղթապանակներում + `finance.html/js/css` |
| Մրցակիցներ `/competitors` | `competitor_*` + `competitors.html/js/css`, `app/integrations/instagram_discovery.py` |
| Ընդհանուր | `templates/base.html` (sidebar, mobile nav), `static/css/main.css` (թեմա, `.card`, `.tint tint-*`) |

## Token-ների խնայողություն
- Կարդալ միայն նշված ֆայլը/բաժինը։ Նախ `Grep`, հետո `Read`՝ offset/limit-ով, ոչ ամբողջ ֆայլը։
- Փոքր CSS/տեքստային փոփոխությունից հետո **screenshot չանել**, եթե չեն խնդրել։ Եթե պետք է՝ միայն մեկ լայնություն և մեկ հատված (`--clip`)։
- Screenshot-ի գործիքը՝ `scripts/dev/shot.py`, նորից չգրել (օգտագործումը՝ ֆայլի սկզբում)։
- Ամփոփումը կարճ. ինչ փոխվեց + որ ֆայլում։

## Գործարկում
`.venv\Scripts\python.exe run.py` → http://127.0.0.1:8000 · դեմո՝ `scripts\seed.py --reset | --analytics | --finance | --competitors`
