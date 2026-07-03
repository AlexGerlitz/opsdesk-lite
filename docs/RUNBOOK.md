# Runbook

## Local Test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -q
python3 scripts/reviewer_replay.py
python3 scripts/support_diagnostics.py
python3 scripts/privacy_audit.py
```

## Reviewer Replay

Run the no-Docker replay when a reviewer wants proof without starting services:

```bash
python3 scripts/reviewer_replay.py
```

It creates a temporary SQLite database, posts a synthetic webhook request, proves webhook
idempotency, checks the operator queue, performs a status handoff, dispatches the outbox, reads
metrics, and verifies the OpenAPI paths that define the backend slice. A non-zero exit means at
least one proof check failed.

## Support Diagnostics Replay

Run the no-Docker diagnostics proof when a reviewer wants to see application-support behavior:

```bash
python3 scripts/support_diagnostics.py
```

It posts a synthetic webhook request, confirms that diagnostics detect due integration work,
dispatches the outbox, and confirms that the final reconciliation report is clean.

## Docker Run

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:8000/docs`.

## Smoke

In another terminal:

```bash
python3 scripts/smoke.py
```

Expected result:

```json
{
  "health": {"status": "ok", "app": "OpsDesk Reviewer Replay"},
  "ticket_id": 1,
  "queue_size": 1,
  "outbox_size": 1,
  "outbox_dispatch": {"scanned": 1, "sent": 1, "failed": 0},
  "diagnostics_ok": true,
  "metrics": {
    "total_tickets": 1,
    "open_tickets": 1,
    "by_status": [{"key": "triaged", "count": 1}],
    "outbox_by_status": [{"key": "sent", "count": 1}]
  }
}
```

## Worker

Run one SLA scan:

```bash
python3 -m opsdesk.worker --once
```

## Integration Outbox

Every created ticket writes a `ticket.created` event into `outbox_events`.
Webhook intake is idempotent by `source:payload_id`, so a duplicate webhook returns the same ticket
and does not create a second event.

Check and dispatch due events:

```bash
curl http://localhost:8000/api/v1/admin/outbox
curl -X POST http://localhost:8000/api/v1/admin/outbox/dispatch \
  -H "Content-Type: application/json" \
  -d '{"limit":10}'
```

## Metrics Summary

Check the reviewable support summary:

```bash
curl http://localhost:8000/api/v1/admin/metrics/summary
```

The response groups tickets by status, priority, source channel, SLA breach state, and outbox
status. It is intentionally small so a reviewer can inspect the SQL/API boundary quickly.

## Diagnostics

Check the support reconciliation report:

```bash
curl http://localhost:8000/api/v1/admin/diagnostics/reconciliation
```

The response reports due integration work, failed outbox events, breached open tickets, and tickets
missing a `ticket.created` event. Details use synthetic IDs only and avoid private customer data.

## Troubleshooting

- Database connection fails: check `DATABASE_URL` and `docker compose ps`.
- Redis is unavailable: API still works, but SLA worker reports no Redis event.
- Outbox event remains pending: run `/api/v1/admin/outbox/dispatch` and inspect `last_error`.
- OpenAPI missing routes: run `pytest -q`, especially `tests/test_contracts.py`.
