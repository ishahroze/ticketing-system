# AI-Powered Ticketing System

A customer support ticketing system with an AI triage pipeline built on
**Django**, **Django REST Framework**, **PostgreSQL**, **LangGraph**, and the
**OpenAI API**.

When a ticket is analyzed, a LangGraph workflow runs the ticket text through
four chained steps, each an OpenAI call:

```
classify_ticket  →  analyze_sentiment  →  summarize_ticket  →  draft_response
```

- **classify_ticket** – suggests a category and priority (low/medium/high/urgent)
- **analyze_sentiment** – detects customer sentiment (positive/neutral/negative)
- **summarize_ticket** – produces a 1-2 sentence summary for agents
- **draft_response** – drafts a suggested first reply for the agent to review/send

Results are saved back onto the `Ticket` row (`ai_suggested_category`,
`ai_suggested_priority`, `ai_sentiment`, `ai_summary`, `ai_suggested_response`,
`ai_confidence`).

## Project layout

```
config/            Django project settings, root urls, wsgi/asgi
accounts/          Custom User model (roles: customer/agent/admin), auth endpoints
tickets/           Ticket, Category, Comment models + DRF viewsets
ai_engine/         LangGraph pipeline (graph.py) + service layer (services.py)
requirements.txt
docker-compose.yml Postgres + web app
Dockerfile
.env.example
```

## Setup

### 1. Clone & configure environment

```bash
cp .env.example .env
# edit .env: set OPENAI_API_KEY and PostgreSQL credentials
```

### Using a free provider instead of OpenAI

OpenAI's API is pay-as-you-go (a ChatGPT Plus subscription does **not** include
API access, and new accounts no longer get free trial credits). If you don't
want to pay, this project can point at any OpenAI-compatible free provider —
e.g. **Groq** — instead, with zero code changes:

```env
OPENAI_API_KEY=gsk_your_groq_key_here
OPENAI_MODEL=llama-3.3-70b-versatile
OPENAI_BASE_URL=https://api.groq.com/openai/v1
```

Get a free Groq key at https://console.groq.com/keys (no credit card
required). Leave `OPENAI_BASE_URL` blank to use real OpenAI instead.

### 2a. Run with Docker (recommended)

```bash
docker compose up --build
```

This starts PostgreSQL and the Django app, runs migrations, and serves the
API at `http://localhost:8000/`.

Then seed some demo data (in a second terminal):

```bash
docker compose exec web python manage.py seed_demo_data
```

### 2b. Run locally without Docker

Requires a running PostgreSQL instance matching your `.env` settings.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo_data     # creates admin/agent/customer + demo tickets
python manage.py runserver
```

Demo accounts created by `seed_demo_data`:

| username    | password       | role     |
|-------------|----------------|----------|
| admin       | admin12345     | admin (superuser) |
| agent1      | agent12345     | agent    |
| customer1   | customer12345  | customer |

## Authentication

Token-based auth via DRF's `TokenAuthentication`.

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -d "username=jane&password=SecurePass123&email=jane@example.com"

# Login (returns a token)
curl -X POST http://localhost:8000/api/auth/login/ \
  -d "username=jane&password=SecurePass123"

# Use the token
curl http://localhost:8000/api/tickets/ -H "Authorization: Token <token>"
```

## API Endpoints

| Method | Endpoint                              | Description                                   |
|--------|----------------------------------------|-----------------------------------------------|
| POST   | `/api/auth/register/`                 | Create an account                             |
| POST   | `/api/auth/login/`                    | Get an auth token                             |
| GET    | `/api/auth/me/`                       | Current user profile                          |
| GET    | `/api/tickets/`                       | List tickets (customers see only their own)   |
| POST   | `/api/tickets/`                       | Create a ticket                               |
| GET    | `/api/tickets/{id}/`                  | Ticket detail (incl. AI fields + comments)    |
| PATCH  | `/api/tickets/{id}/`                  | Update a ticket                               |
| POST   | `/api/tickets/{id}/analyze/`          | **Run the LangGraph AI triage pipeline**      |
| POST   | `/api/tickets/{id}/apply_ai_suggestions/` | Apply AI-suggested category/priority (agent/admin) |
| POST   | `/api/tickets/{id}/assign/`           | Assign ticket to an agent (agent/admin)       |
| GET    | `/api/categories/`                    | List categories                               |
| POST   | `/api/categories/`                    | Create a category (agent/admin)               |
| GET    | `/api/comments/`                      | List comments                                 |
| POST   | `/api/comments/`                      | Add a comment to a ticket                     |

Ticket list/detail support filtering, search, and ordering, e.g.:

```
GET /api/tickets/?status=open&priority=high
GET /api/tickets/?search=login
GET /api/tickets/?ordering=-created_at
```

### Triggering AI analysis

```bash
curl -X POST http://localhost:8000/api/tickets/1/analyze/ \
  -H "Authorization: Token <token>"
```

Response includes the full ticket with populated `ai_*` fields.

By default AI analysis only runs when this endpoint is called, so API costs
are predictable. To auto-run the pipeline the instant a ticket is created,
set `AI_AUTO_ANALYZE_ON_CREATE=True` in `.env` (see `tickets/signals.py`).
For production, wire that call into an async task queue (e.g. Celery) instead
of running it synchronously in the request/response cycle.

## Roles & permissions

- **Customer**: can create tickets and see/comment on only their own.
- **Agent / Admin**: can see all tickets, assign them, trigger AI analysis,
  apply AI suggestions, and manage categories.

## Admin site

Visit `/admin/` and log in with the seeded `admin` account to browse and
edit tickets, categories, comments, and users directly.

## Extending

- Swap the synchronous `analyze` action for a Celery task + webhook/websocket
  notification when large-scale async processing is needed.
- Add a `django-channels` consumer to push live ticket updates to agents.
- Extend `ai_engine/graph.py` with more LangGraph nodes (e.g. auto-routing to
  a knowledge base, duplicate-ticket detection, escalation rules).
