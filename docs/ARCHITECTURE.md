# Architecture

OpsDesk Lite is a small backend/API proof project for support and operator workflows.

## Flow

1. A request arrives through `POST /api/v1/tickets` or `POST /api/v1/intake/webhook`.
2. FastAPI validates the payload with Pydantic.
3. SQLAlchemy stores the ticket and an immutable activity log entry.
4. Operators read open work through `GET /api/v1/operator/queue`.
5. Operators move work through explicit status transitions.
6. The SLA worker scans open tickets and marks breached tickets with a log event.
7. Redis receives a lightweight SLA event when it is available.

## Data Boundary

The project uses synthetic data. It should never receive real customer records, phone numbers, chat IDs, admin URLs, tokens, raw logs, or database dumps.

## Why This Shape

This project is intentionally narrow: it demonstrates the backend slice recruiters ask about most often for junior Python roles.

- REST API and OpenAPI.
- SQL state and migrations.
- Docker Compose handoff.
- pytest coverage.
- Small worker/background process.
- Runbook and smoke check.

It is not positioned as senior platform, SRE, Kubernetes, or Terraform ownership.
