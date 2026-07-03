# Runbook

## Local Test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -q
python3 scripts/privacy_audit.py
```

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
  "health": {"status": "ok", "app": "OpsDesk Lite"},
  "ticket_id": 1,
  "queue_size": 1,
  "outbox_size": 1,
  "outbox_dispatch": {"scanned": 1, "sent": 1, "failed": 0}
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

## Troubleshooting

- Database connection fails: check `DATABASE_URL` and `docker compose ps`.
- Redis is unavailable: API still works, but SLA worker reports no Redis event.
- Outbox event remains pending: run `/api/v1/admin/outbox/dispatch` and inspect `last_error`.
- OpenAPI missing routes: run `pytest -q`, especially `tests/test_contracts.py`.
