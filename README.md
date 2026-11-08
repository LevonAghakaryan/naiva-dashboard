# naiva-dashboard

SaaS dashboard Instagram բլոգերների համար (աշխատանքային անուն՝ **Creatorly**)։
Վիճակագրություն, նամակներ ու բոտեր, ֆինանսներ, մրցակիցներ և AI օգնական։ Ինտերֆեյսը հայերեն է։

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · MySQL 8 · Jinja2 + vanilla JS · Chart.js

## Գործարկում

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

copy .env.example .env          # լրացրեք DB_PASSWORD և ENCRYPTION_KEY
mysql -u root -p -e "source db/schema.sql"
.venv\Scripts\python.exe scripts\seed.py   # դեմո տվյալներ (@ani.travels)
.venv\Scripts\python.exe run.py            # http://127.0.0.1:8000
```

API-ի նկարագրությունը՝ http://127.0.0.1:8000/docs

## Կառուցվածք

```
core/          config, DB, գաղտնագրում
app/models/    SQLAlchemy մոդելներ
app/schemas/   API-ի պատասխանների ձևը (Pydantic)
app/repositories/  միայն DB հարցումներ
app/services/  բիզնես լոգիկա
app/routers/   API + HTML էջեր
templates/, static/   frontend
db/schema.sql  MySQL սխեմա
scripts/       seed և այլ գործիքներ
```

Մանրամասն պլանը և որոշումները՝ [PROJECT.md](PROJECT.md)։

## Կարգավիճակ

- [x] Instagram վիճակագրություն (դեմո տվյալներով)
- [x] Ֆինանսներ (դեմո տվյալներով, գործարքներ և համագործակցություններ՝ CRUD)
- [ ] Գլխավոր, Նամակներ ու բոտեր, Մրցակիցներ, AI օգնական
- [ ] Instagram API-ի իրական միացում
