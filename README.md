# OpsDesk Lite

[![CI](https://github.com/AlexGerlitz/opsdesk-lite/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AlexGerlitz/opsdesk-lite/actions/workflows/ci.yml)

FastAPI/PostgreSQL support-desk backend: ticket intake -> validation -> database state -> operator queue -> integration outbox -> SLA worker -> metrics summary -> API tests -> Docker handoff.

This is a public-safe backend portfolio project. It uses synthetic support tickets only and does not contain customer names, phone numbers, chat IDs, admin URLs, raw logs, tokens, database dumps, or private production code.

## 60-Second Reviewer Snapshot

- **Role signal:** Junior Python Backend / API Automation, Internal Tools, QA/API Python, and Support Engineer with Python when the work is API/backend-heavy.
- **Backend slice:** support request intake -> Pydantic validation -> SQLAlchemy model -> operator queue -> explicit status transition -> idempotent integration outbox -> SLA worker event -> SQL metrics summary.
- **Review proof:** pytest coverage, ruff, CI, Docker Compose, PostgreSQL migration, Redis-backed worker path, smoke script, and public privacy audit.
- **Profile / contact route:** [GitHub recruiter handoff](https://github.com/AlexGerlitz/AlexGerlitz/blob/main/GITHUB_RECRUITER_HANDOFF.md), [LinkedIn Recruiter Packet](https://alexgerlitz.github.io/AlexGerlitz/linkedin-recruiter-packet.html), and [PDF resume](https://alexgerlitz.github.io/AlexGerlitz/output/pdf/alex-gerlitz-python-backend-automation-resume.pdf).

Shortest proof path: run `pytest -q`, inspect `src/opsdesk/service.py`, open `/docs`, then run `python scripts/smoke.py` against the API.

## What This Proves

- FastAPI REST API with OpenAPI/Swagger.
- PostgreSQL schema and migration path.
- SQLAlchemy models and explicit status transitions.
- Webhook idempotency and outbox dispatch/retry boundary.
- Reporting endpoint for queue, priority, source-channel, SLA, and outbox state.
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
- Metrics summary: http://localhost:8000/api/v1/admin/metrics/summary

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
- `src/opsdesk/service.py` - ticket workflow, idempotent webhook intake, and outbox dispatch.
- `GET /api/v1/admin/metrics/summary` - SQL aggregation for reviewable support metrics.
- `migrations/001_init.sql` - PostgreSQL schema.
- `scripts/smoke.py` - live API smoke check.
- `scripts/privacy_audit.py` - public-safe repository audit.
- `docs/ARCHITECTURE.md` - backend flow and boundaries.
- `docs/RUNBOOK.md` - setup, smoke, and troubleshooting.

## Recruiter Summary

I can take one backend/API support slice and make it reviewable: input validation, database state, operator workflow, status handoff, idempotent integration event, retryable outbox, SLA check, SQL metrics, tests, logs, and Docker run instructions.

## Boundaries

This project intentionally stays in the backend/API ownership lane. Docker and Redis are supporting handoff tools here, not the main job identity.
