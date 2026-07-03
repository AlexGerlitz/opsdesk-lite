from __future__ import annotations

from datetime import UTC, datetime, timedelta

from opsdesk.models import OutboxStatus, Ticket, TicketPriority, TicketStatus
from opsdesk.service import list_outbox


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


def item_by_key(report: dict, key: str) -> dict:
    return {item["key"]: item for item in report["items"]}[key]


def test_reconciliation_reports_due_outbox_then_clears_after_dispatch(client):
    client.post("/api/v1/intake/webhook", json=webhook_payload())

    before = client.get("/api/v1/admin/diagnostics/reconciliation")
    assert before.status_code == 200
    before_report = before.json()
    assert before_report["ok"] is True
    assert item_by_key(before_report, "due_outbox_events")["count"] == 1

    dispatch = client.post("/api/v1/admin/outbox/dispatch", json={"limit": 10})
    assert dispatch.json() == {"scanned": 1, "sent": 1, "failed": 0}

    after_report = client.get("/api/v1/admin/diagnostics/reconciliation").json()
    assert after_report["ok"] is True
    assert item_by_key(after_report, "due_outbox_events")["count"] == 0
    assert item_by_key(after_report, "failed_outbox_events")["count"] == 0


def test_reconciliation_flags_failed_outbox_event(client, db_session):
    client.post("/api/v1/intake/webhook", json=webhook_payload(payload_id="lead-1002"))
    event = list_outbox(db_session)[0]
    event.status = OutboxStatus.failed
    event.attempts = 2
    event.last_error = "temporary downstream timeout"
    event.next_attempt_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    report = client.get("/api/v1/admin/diagnostics/reconciliation").json()

    assert report["ok"] is False
    assert item_by_key(report, "failed_outbox_events")["count"] == 1
    assert "temporary downstream timeout" in item_by_key(report, "failed_outbox_events")[
        "details"
    ][0]


def test_reconciliation_flags_ticket_without_created_event(client, db_session):
    ticket = Ticket(
        requester_name="Synthetic User",
        requester_email="synthetic@example.test",
        channel="web",
        subject="Manual database recovery",
        message="A manually inserted support record needs reconciliation checks.",
        priority=TicketPriority.high,
        status=TicketStatus.new,
        sla_due_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    db_session.add(ticket)
    db_session.commit()

    report = client.get("/api/v1/admin/diagnostics/reconciliation").json()

    assert report["ok"] is False
    assert item_by_key(report, "tickets_missing_created_event")["count"] == 1
    assert item_by_key(report, "tickets_missing_created_event")["details"] == [
        f"ticket_id={ticket.id}"
    ]
