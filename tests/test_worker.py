from __future__ import annotations

from datetime import UTC, datetime, timedelta

from opsdesk.models import Ticket
from opsdesk.schemas import TicketCreate
from opsdesk.service import create_ticket
from opsdesk.worker import scan_sla


class FakeRedis:
    def __init__(self):
        self.events = []

    def xadd(self, stream, payload):
        self.events.append((stream, payload))


def test_sla_scan_marks_overdue_ticket_once(db_session):
    ticket = create_ticket(
        db_session,
        TicketCreate(
            requester_name="Demo Operator",
            requester_email="operator@example.test",
            channel="web",
            subject="Queue stuck",
            message="The operator queue is stuck and needs a backend status check.",
            priority="high",
        ),
    )
    ticket.sla_due_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    fake_redis = FakeRedis()
    result = scan_sla(db_session, redis_conn=fake_redis)
    assert result == {"scanned": 1, "breached": 1, "redis_event_published": True}

    refreshed = db_session.get(Ticket, ticket.id)
    assert refreshed is not None
    assert refreshed.sla_breached is True
    assert fake_redis.events[0][0] == "opsdesk:sla_events"

    second = scan_sla(db_session, redis_conn=fake_redis)
    assert second["breached"] == 0
