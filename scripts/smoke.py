from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def request(method: str, path: str, payload: dict | None = None) -> dict | list:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    health = request("GET", "/health")
    ticket = request(
        "POST",
        "/api/v1/tickets",
        {
            "requester_name": "Demo Operator",
            "requester_email": "operator@example.test",
            "channel": "web",
            "subject": "Payment status mismatch",
            "message": "Invoice is paid but the admin queue still shows pending.",
            "priority": "high",
        },
    )
    queue = request("GET", "/api/v1/operator/queue")
    outbox_before = request("GET", "/api/v1/admin/outbox")
    dispatch = request("POST", "/api/v1/admin/outbox/dispatch", {"limit": 10})
    request(
        "PATCH",
        f"/api/v1/tickets/{ticket['id']}/status",
        {"status": "triaged", "actor": "demo", "note": "validated from smoke script"},
    )
    metrics = request("GET", "/api/v1/admin/metrics/summary")
    result = {
        "health": health,
        "ticket_id": ticket["id"],
        "queue_size": len(queue),
        "outbox_size": len(outbox_before),
        "outbox_dispatch": dispatch,
        "metrics": {
            "total_tickets": metrics["total_tickets"],
            "open_tickets": metrics["open_tickets"],
            "by_status": metrics["by_status"],
            "outbox_by_status": metrics["outbox_by_status"],
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
