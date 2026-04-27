# BoardGameCafe

A Flask web application for managing a board game café — bookings, reservations, payments, game catalogue, and staff operations — built with Domain-Driven Design.

## Quick start

### Prerequisites

- Python 3.11+
- A `.env` file in `boardgame_cafe/` (see [Environment variables](#environment-variables))

### Windows

```powershell
py -m venv .venv
.\startup.bat --install-deps   # first time or after requirements change
.\startup.bat                  # subsequent starts
```

### macOS / Linux

```bash
python3 -m venv .venv
chmod +x startup.sh
./startup.sh --install-deps    # first time or after requirements change
./startup.sh
```

The app runs on **http://127.0.0.1:5000** by default.

---

## Docker (recommended for full stack)

Runs Flask, Celery worker, and Redis together with demo data pre-loaded:

```bash
docker compose up --build
```

App will be available on **http://localhost:5001**.

---

## Demo accounts (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | AdminPw123! |
| Steward | steward@example.com | StewardPw1! |
| Customer | customer accounts use | Password1! |

Seed demo data manually:

```powershell
.\.venv\Scripts\python.exe boardgame_cafe/scripts/seed_demo_data.py
```

---

## Environment variables

Create `boardgame_cafe/.env`. Minimum for local development:

```env
SECRET_KEY=change-me
FLASK_ENV=development
DATABASE_URL=sqlite:///boardgame_cafe.db

# Stripe (use test keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (optional locally)
MAIL_SERVER=localhost
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=

# Redis / Celery (only needed for background tasks and realtime)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/2
```

---

## Background tasks and realtime

Email notifications and realtime SSE events are handled by Celery + Redis.

Start Redis locally (or use Docker), then start the worker in a separate terminal:

```powershell
.\.venv\Scripts\python.exe -m celery -A boardgame_cafe.src.celery_worker.celery_app worker -l info
```

Realtime event stream endpoint (used by the frontend via `EventSource`):

```
GET /api/events/stream
```

Without Redis running, the app still works — background tasks and realtime updates are simply skipped.

---

## Running tests

```powershell
.\.venv\Scripts\pytest
```

Tests live in `boardgame_cafe/tests/` and are configured via `pytest.ini` at the project root.

---

## Project structure

```
BoardGameCafe/
├── run.py                        
├── startup.bat / startup.sh      # Start scripts
├── docker-compose.yml
├── pytest.ini
└── boardgame_cafe/
    ├── src/
    │   ├── app.py                
    │   ├── config.py             
    │   ├── features/             # DDD features
    │   │   ├── bookings/
    │   │   ├── games/
    │   │   ├── payments/
    │   │   ├── reservations/
    │   │   ├── tables/
    │   │   ├── users/
    │   │   └── waitlists/
    │   ├── shared/               # Cross-cutting infrastructure
    │   └── ui/                   # Flask page blueprints
    ├── frontend/
    │   ├── templates/            
    │   └── static/               
    ├── scripts/
    │   └── seed_demo_data.py     # Demo data seeder
    ├── tests/
    └── requirements.txt
```

Each feature follows the same layered structure: `domain → application → infrastructure → presentation`.