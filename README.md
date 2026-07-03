# OpsDesk Lite

FastAPI/PostgreSQL support-desk backend: ticket intake -> validation -> database state -> operator queue -> SLA worker -> API tests -> Docker handoff.

This is a public-safe backend portfolio project. It uses synthetic support tickets only and does not contain customer names, phone numbers, chat IDs, admin URLs, raw logs, tokens, database dumps, or private production code.

## What This Proves

- FastAPI REST API with OpenAPI/Swagger.
- PostgreSQL schema and migration path.
- SQLAlchemy models and explicit status transitions.
- Docker Compose handoff with API, PostgreSQL, Redis, and worker.
- pytest coverage for intake, queue, status changes, SLA scanning, and privacy boundaries.
- Small runbook and smoke script that a reviewer can run without private context.

## First Review Route

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -q
```

Run the API with local Docker services:

```bash
cp .env.example .env
docker compose up --build
```

Open:

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Operator queue: http://localhost:8000/api/v1/operator/queue

## Core API

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "requester_name": "Demo Operator",
    "requester_email": "operator@example.test",
    "channel": "web",
    "subject": "Payment status mismatch",
    "message": "Invoice is paid but the admin queue still shows pending.",
    "priority": "high"
  }'
```

Then inspect the queue:

```bash
curl http://localhost:8000/api/v1/operator/queue
```

## Project Shape

- `src/opsdesk/main.py` - FastAPI routes.
- `src/opsdesk/models.py` - SQLAlchemy tables.
- `src/opsdesk/worker.py` - SLA breach scanner.
- `migrations/001_init.sql` - PostgreSQL schema.
- `scripts/smoke.py` - live API smoke check.
- `scripts/privacy_audit.py` - public-safe repository audit.
- `docs/ARCHITECTURE.md` - backend flow and boundaries.
- `docs/RUNBOOK.md` - setup, smoke, and troubleshooting.

## Recruiter Summary

I can take one backend/API support slice and make it reviewable: input validation, database state, operator workflow, status handoff, SLA check, tests, logs, and Docker run instructions.

## Boundaries

This project intentionally does not claim senior DevOps/SRE/platform ownership. Docker and Redis are supporting backend handoff tools here, not the main job identity.
