from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from opsdesk.config import get_settings
from opsdesk.models import (
    OPEN_STATUSES,
    ActivityLog,
    OutboxEvent,
    OutboxStatus,
    Ticket,
    TicketPriority,
    TicketStatus,
)
from opsdesk.schemas import ActivityCreate, TicketCreate, TicketStatusUpdate, WebhookTicket

ALLOWED_TRANSITIONS = {
    TicketStatus.new: {
        TicketStatus.triaged,
        TicketStatus.waiting_customer,
        TicketStatus.resolved,
    },
    TicketStatus.triaged: {TicketStatus.waiting_customer, TicketStatus.resolved},
    TicketStatus.waiting_customer: {TicketStatus.triaged, TicketStatus.resolved},
    TicketStatus.resolved: set(),
}


def sla_due_for(priority: TicketPriority, now: datetime | None = None) -> datetime:
    settings = get_settings()
    base = now or datetime.now(UTC)
    if priority in {TicketPriority.high, TicketPriority.urgent}:
        return base + timedelta(minutes=settings.sla_minutes_high)
    if priority == TicketPriority.low:
        return base + timedelta(minutes=settings.sla_minutes_normal * 2)
    return base + timedelta(minutes=settings.sla_minutes_normal)


def add_activity(
    db: Session, ticket: Ticket, event_type: str, actor: str, note: str = ""
) -> ActivityLog:
    activity = ActivityLog(ticket=ticket, event_type=event_type, actor=actor, note=note)
    db.add(activity)
    return activity


def enqueue_outbox_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    payload: dict[str, object],
    idempotency_key: str,
) -> OutboxEvent:
    existing = db.scalar(select(OutboxEvent).where(OutboxEvent.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        idempotency_key=idempotency_key,
        payload_json=json.dumps(payload, sort_keys=True),
    )
    db.add(event)
    return event


def create_ticket(db: Session, payload: TicketCreate, *, actor: str = "intake") -> Ticket:
    if payload.external_ref:
        existing = db.scalar(select(Ticket).where(Ticket.external_ref == payload.external_ref))
        if existing is not None:
            return get_ticket(db, existing.id)
    ticket = Ticket(
        external_ref=payload.external_ref,
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        channel=payload.channel,
        subject=payload.subject,
        message=payload.message,
        priority=payload.priority,
        sla_due_at=sla_due_for(payload.priority),
    )
    db.add(ticket)
    db.flush()
    add_activity(db, ticket, "ticket_created", actor, f"created from {payload.channel}")
    enqueue_outbox_event(
        db,
        event_type="ticket.created",
        aggregate_type="ticket",
        aggregate_id=ticket.id,
        payload={
            "ticket_id": ticket.id,
            "external_ref": ticket.external_ref,
            "channel": ticket.channel,
            "priority": ticket.priority.value,
        },
        idempotency_key=f"ticket.created:{ticket.external_ref or ticket.id}",
    )
    db.commit()
    db.refresh(ticket)
    return get_ticket(db, ticket.id)


def create_ticket_from_webhook(db: Session, payload: WebhookTicket) -> Ticket:
    ticket_payload = TicketCreate(
        external_ref=f"{payload.source}:{payload.payload_id}",
        requester_name=payload.requester_name,
        requester_email=payload.requester_email,
        channel=payload.source,
        subject=f"{payload.source} request {payload.payload_id}",
        message=payload.text,
        priority=payload.priority,
    )
    return create_ticket(db, ticket_payload, actor="webhook")


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.scalar(
        select(Ticket).options(selectinload(Ticket.activities)).where(Ticket.id == ticket_id)
    )
    if ticket is None:
        raise LookupError(f"ticket not found: {ticket_id}")
    return ticket


def list_queue(db: Session, status: TicketStatus | None = None, limit: int = 50) -> list[Ticket]:
    query = (
        select(Ticket).order_by(Ticket.sla_breached.desc(), Ticket.sla_due_at.asc()).limit(limit)
    )
    if status is not None:
        query = query.where(Ticket.status == status)
    else:
        query = query.where(Ticket.status.in_(OPEN_STATUSES))
    return list(db.scalars(query))


def list_outbox(
    db: Session, status: OutboxStatus | None = None, limit: int = 50
) -> list[OutboxEvent]:
    query = select(OutboxEvent).order_by(OutboxEvent.created_at.asc()).limit(limit)
    if status is not None:
        query = query.where(OutboxEvent.status == status)
    return list(db.scalars(query))


def dispatch_pending_outbox(
    db: Session, *, limit: int = 50, now: datetime | None = None
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    events = list(
        db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.status.in_([OutboxStatus.pending, OutboxStatus.failed]))
            .where(OutboxEvent.next_attempt_at <= current_time)
            .order_by(OutboxEvent.next_attempt_at.asc(), OutboxEvent.id.asc())
            .limit(limit)
        )
    )
    sent = 0
    failed = 0
    for event in events:
        try:
            json.loads(event.payload_json)
            event.status = OutboxStatus.sent
            event.attempts += 1
            event.last_error = None
            sent += 1
        except ValueError as exc:
            event.status = OutboxStatus.failed
            event.attempts += 1
            event.last_error = str(exc)
            event.next_attempt_at = current_time + timedelta(minutes=5)
            failed += 1
    db.commit()
    return {"scanned": len(events), "sent": sent, "failed": failed}


def update_ticket_status(db: Session, ticket_id: int, payload: TicketStatusUpdate) -> Ticket:
    ticket = get_ticket(db, ticket_id)
    if payload.status == ticket.status:
        add_activity(db, ticket, "status_unchanged", payload.actor, payload.note)
    elif payload.status not in ALLOWED_TRANSITIONS[ticket.status]:
        raise ValueError(f"cannot move ticket from {ticket.status.value} to {payload.status.value}")
    else:
        previous = ticket.status.value
        ticket.status = payload.status
        add_activity(
            db,
            ticket,
            "status_changed",
            payload.actor,
            f"{previous} -> {payload.status.value}. {payload.note}".strip(),
        )
    if payload.assignee:
        ticket.assignee = payload.assignee
        add_activity(db, ticket, "assigned", payload.actor, payload.assignee)
    db.commit()
    return get_ticket(db, ticket.id)


def append_activity(db: Session, ticket_id: int, payload: ActivityCreate) -> Ticket:
    ticket = get_ticket(db, ticket_id)
    add_activity(db, ticket, payload.event_type, payload.actor, payload.note)
    db.commit()
    return get_ticket(db, ticket.id)
