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


def test_create_ticket_and_queue_flow(client):
    response = client.post("/api/v1/tickets", json=ticket_payload())
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["status"] == "new"
    assert ticket["priority"] == "high"
    assert ticket["sla_breached"] is False
    assert ticket["activities"][0]["event_type"] == "ticket_created"

    queue_response = client.get("/api/v1/operator/queue")
    assert queue_response.status_code == 200
    queue = queue_response.json()
    assert len(queue) == 1
    assert queue[0]["subject"] == "Payment status mismatch"


def test_status_transition_logs_activity(client):
    ticket = client.post("/api/v1/tickets", json=ticket_payload()).json()
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "triaged", "actor": "operator-a", "note": "checked backend state"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "triaged"
    events = [activity["event_type"] for activity in updated["activities"]]
    assert "ticket_created" in events
    assert "status_changed" in events


def test_invalid_transition_is_rejected(client):
    ticket = client.post("/api/v1/tickets", json=ticket_payload()).json()
    resolved = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "resolved", "actor": "operator-a", "note": "done"},
    )
    assert resolved.status_code == 200

    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "triaged", "actor": "operator-a"},
    )
    assert response.status_code == 422


def test_webhook_creates_external_reference(client):
    response = client.post(
        "/api/v1/intake/webhook",
        json={
            "source": "telegram_mock",
            "payload_id": "msg-1001",
            "requester_name": "Synthetic User",
            "requester_email": "synthetic@example.test",
            "text": "Need help because the status did not update after payment.",
            "priority": "normal",
        },
    )
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["external_ref"] == "telegram_mock:msg-1001"
    assert ticket["channel"] == "telegram_mock"
