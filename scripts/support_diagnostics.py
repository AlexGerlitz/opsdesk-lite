from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from reviewer_replay import _client_with_temp_db


def _item(report: dict[str, Any], key: str) -> dict[str, Any]:
    return {item["key"]: item for item in report["items"]}[key]


def run_diagnostics() -> dict[str, Any]:
    with TemporaryDirectory() as tmp_dir:
        with _client_with_temp_db(Path(tmp_dir) / "diagnostics.db") as client:
            health = client.get("/health").json()
            created = client.post(
                "/api/v1/intake/webhook",
                json={
                    "source": "crm_mock",
                    "payload_id": "lead-2001",
                    "requester_name": "Synthetic User",
                    "requester_email": "synthetic@example.test",
                    "text": "Need help because the payment status did not update in the queue.",
                    "priority": "high",
                },
            ).json()
            before = client.get("/api/v1/admin/diagnostics/reconciliation").json()
            dispatch = client.post("/api/v1/admin/outbox/dispatch", json={"limit": 10}).json()
            after = client.get("/api/v1/admin/diagnostics/reconciliation").json()

    checks = {
        "health_ok": health["status"] == "ok",
        "ticket_created": created["external_ref"] == "crm_mock:lead-2001",
        "due_outbox_detected": _item(before, "due_outbox_events")["count"] == 1,
        "dispatch_sent": dispatch == {"scanned": 1, "sent": 1, "failed": 0},
        "final_reconciliation_ok": after["ok"] is True
        and all(item["count"] == 0 for item in after["items"]),
    }
    return {
        "scenario": (
            "synthetic webhook -> support diagnostics detects due integration work -> "
            "outbox dispatch -> clean reconciliation report"
        ),
        "checks": checks,
        "before": {
            "ok": before["ok"],
            "due_outbox_events": _item(before, "due_outbox_events"),
            "failed_outbox_events": _item(before, "failed_outbox_events"),
        },
        "dispatch": dispatch,
        "after": {
            "ok": after["ok"],
            "items": after["items"],
        },
    }


def main() -> int:
    result = run_diagnostics()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
