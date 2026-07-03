from __future__ import annotations


def ticket_payload(**overrides):
    payload = {
        "requester_name": "Demo Operator",
        "requester_email": "operator@example.test",
        "channel": "web",
        "subject": "Payment status mismatch",
        "message": "Invoice is paid but the admin queue still shows pending.",
        "priority": "high",
    }
    payload.update(overrides)
    return payload


def bucket(summary: dict, group: str) -> dict[str, int]:
    return {item["key"]: item["count"] for item in summary[group]}


def test_metrics_summary_groups_queue_and_outbox_state(client):
    first = client.post("/api/v1/tickets", json=ticket_payload()).json()
    client.post(
        "/api/v1/intake/webhook",
        json={
            "source": "crm_mock",
            "payload_id": "lead-1001",
            "requester_name": "Synthetic User",
            "requester_email": "synthetic@example.test",
            "text": "Need help because the status did not update after payment.",
            "priority": "normal",
        },
    )
    client.patch(
        f"/api/v1/tickets/{first['id']}/status",
        json={"status": "triaged", "actor": "operator-a", "note": "checked backend state"},
    )

    response = client.get("/api/v1/admin/metrics/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_tickets"] == 2
    assert summary["open_tickets"] == 2
    assert summary["sla_breached_tickets"] == 0
    assert bucket(summary, "by_status") == {"new": 1, "triaged": 1}
    assert bucket(summary, "by_priority") == {"high": 1, "normal": 1}
    assert bucket(summary, "by_channel") == {"crm_mock": 1, "web": 1}
    assert bucket(summary, "outbox_by_status") == {"pending": 2}
