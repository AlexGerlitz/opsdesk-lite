# Architecture

OpsDesk Lite is a small backend/API proof project for support and operator workflows.

## Flow

1. A request arrives through `POST /api/v1/tickets` or `POST /api/v1/intake/webhook`.
2. FastAPI validates the payload with Pydantic.
3. SQLAlchemy stores the ticket and an immutable activity log entry.
4. The same transaction writes a `ticket.created` outbox event with an idempotency key.
5. Operators read open work through `GET /api/v1/operator/queue`.
6. Operators move work through explicit status transitions.
7. The SLA worker scans open tickets and marks breached tickets with a log event.
8. Redis receives a lightweight SLA event when it is available.
9. The outbox dispatch route marks due integration events as sent and supports retrying failed events.
10. The metrics summary route groups ticket and outbox state for a support lead or reviewer.

## Data Boundary

The project uses synthetic data. It should never receive real customer records, phone numbers, chat IDs, admin URLs, tokens, raw logs, or database dumps.

## Why This Shape

This project is intentionally narrow: it demonstrates the backend slice recruiters ask about most often for junior Python roles.

- REST API and OpenAPI.
- SQL state and migrations.
- Webhook idempotency and outbox/retry boundary.
- SQL aggregation for queue, priority, source-channel, SLA, and outbox state.
- Docker Compose handoff.
- pytest coverage.
- Small worker/background process.
- Runbook and smoke check.

It stays in the backend/API ownership lane; infrastructure tools are only handoff support.
