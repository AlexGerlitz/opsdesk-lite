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
  "queue_size": 1
}
```

## Worker

Run one SLA scan:

```bash
python3 -m opsdesk.worker --once
```

## Troubleshooting

- Database connection fails: check `DATABASE_URL` and `docker compose ps`.
- Redis is unavailable: API still works, but SLA worker reports no Redis event.
- OpenAPI missing routes: run `pytest -q`, especially `tests/test_contracts.py`.
