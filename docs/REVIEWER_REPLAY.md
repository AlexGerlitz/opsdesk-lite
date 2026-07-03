# Reviewer Replay

This is the fastest technical proof path for OpsDesk Reviewer Replay when Docker is not needed.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
python3 scripts/reviewer_replay.py
python3 scripts/support_diagnostics.py
```

The replay uses synthetic data only and runs against a temporary SQLite database. It proves:

- webhook intake creates backend state;
- duplicate webhook payloads are idempotent;
- the operator queue exposes open work;
- status handoff records assignee and activity history;
- outbox dispatch reports sent/failed counts;
- metrics aggregate queue, priority, source channel, and outbox state;
- support diagnostics expose due integration work and reconciliation state;
- OpenAPI exposes the review-relevant routes.

Expected high-level checks:

```json
{
  "health_ok": true,
  "idempotent_webhook": true,
  "queue_contains_ticket": true,
  "status_handoff_triaged": true,
  "assignee_recorded": true,
  "outbox_written_once": true,
  "outbox_dispatched": true,
  "metrics_total_tickets": true,
  "openapi_paths_present": true
}
```

The diagnostics replay separately proves:

```json
{
  "due_outbox_detected": true,
  "dispatch_sent": true,
  "final_reconciliation_ok": true
}
```

This replay is intentionally narrow: it demonstrates a first-job backend/API slice rather than a
full support-desk product.
