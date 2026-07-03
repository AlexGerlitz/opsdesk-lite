from __future__ import annotations

from datetime import UTC, datetime, timedelta

from opsdesk.models import OutboxStatus
from opsdesk.service import dispatch_pending_outbox, list_outbox


def webhook_payload(**overrides):
    payload = {
        "source": "crm_mock",
        "payload_id": "lead-1001",
        "requester_name": "Synthetic User",
        "requester_email": "synthetic@example.test",
        "text": "Need help because the status did not update after payment.",
        "priority": "normal",
    }
    payload.update(overrides)
    return payload


def test_webhook_idempotency_reuses_ticket_and_outbox_event(client, db_session):
    first = client.post("/api/v1/intake/webhook", json=webhook_payload())
    duplicate = client.post("/api/v1/intake/webhook", json=webhook_payload())

    assert first.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]

    events = list_outbox(db_session)
    assert len(events) == 1
    assert events[0].event_type == "ticket.created"
    assert events[0].idempotency_key == "ticket.created:crm_mock:lead-1001"


def test_outbox_dispatch_marks_pending_event_sent(client):
    client.post("/api/v1/intake/webhook", json=webhook_payload())

    response = client.post("/api/v1/admin/outbox/dispatch", json={"limit": 10})
    assert response.status_code == 200
    assert response.json() == {"scanned": 1, "sent": 1, "failed": 0}

    outbox = client.get("/api/v1/admin/outbox").json()
    assert outbox[0]["status"] == "sent"
    assert outbox[0]["attempts"] == 1


def test_failed_outbox_event_can_be_retried(client, db_session):
    client.post("/api/v1/intake/webhook", json=webhook_payload(payload_id="lead-1002"))
    event = list_outbox(db_session)[0]
    event.status = OutboxStatus.failed
    event.attempts = 1
    event.last_error = "temporary downstream timeout"
    event.next_attempt_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    result = dispatch_pending_outbox(db_session, limit=10)

    assert result == {"scanned": 1, "sent": 1, "failed": 0}
    retried = list_outbox(db_session)[0]
    assert retried.status == OutboxStatus.sent
    assert retried.attempts == 2
    assert retried.last_error is None
