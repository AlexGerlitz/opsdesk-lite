from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from opsdesk.config import get_settings
from opsdesk.database import get_db
from opsdesk.models import TicketStatus
from opsdesk.schemas import (
    ActivityCreate,
    MetricsSummary,
    OutboxDispatchRequest,
    OutboxDispatchResult,
    OutboxEventRead,
    QueueItem,
    SlaScanResult,
    TicketCreate,
    TicketRead,
    TicketStatusUpdate,
    WebhookTicket,
)
from opsdesk.service import (
    append_activity,
    create_ticket,
    create_ticket_from_webhook,
    dispatch_pending_outbox,
    get_ticket,
    list_outbox,
    list_queue,
    metrics_summary,
    update_ticket_status,
)
from opsdesk.worker import redis_client, scan_sla

DbSession = Annotated[Session, Depends(get_db)]
QueueLimit = Annotated[int, Query(ge=1, le=200)]

app = FastAPI(
    title="OpsDesk Lite",
    version="0.1.0",
    description="Support-desk backend proof: intake, operator queue, status handoff, SLA scan.",
)


@app.get("/health")
def health(db: DbSession) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ok", "app": get_settings().app_name}


@app.post("/api/v1/tickets", response_model=TicketRead, status_code=201)
def create_ticket_route(payload: TicketCreate, db: DbSession) -> TicketRead:
    try:
        return create_ticket(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/intake/webhook", response_model=TicketRead, status_code=201)
def webhook_route(payload: WebhookTicket, db: DbSession) -> TicketRead:
    try:
        return create_ticket_from_webhook(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/operator/queue", response_model=list[QueueItem])
def queue_route(
    db: DbSession,
    status: TicketStatus | None = None,
    limit: QueueLimit = 50,
) -> list[QueueItem]:
    return list_queue(db, status=status, limit=limit)


@app.get("/api/v1/tickets/{ticket_id}", response_model=TicketRead)
def get_ticket_route(ticket_id: int, db: DbSession) -> TicketRead:
    try:
        return get_ticket(db, ticket_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/v1/tickets/{ticket_id}/status", response_model=TicketRead)
def update_status_route(ticket_id: int, payload: TicketStatusUpdate, db: DbSession) -> TicketRead:
    try:
        return update_ticket_status(db, ticket_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/tickets/{ticket_id}/activity", response_model=TicketRead)
def append_activity_route(ticket_id: int, payload: ActivityCreate, db: DbSession) -> TicketRead:
    try:
        return append_activity(db, ticket_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/admin/sla/scan", response_model=SlaScanResult)
def sla_scan_route(db: DbSession) -> dict[str, int | bool]:
    return scan_sla(db, redis_conn=redis_client())


@app.get("/api/v1/admin/outbox", response_model=list[OutboxEventRead])
def outbox_route(db: DbSession, limit: QueueLimit = 50) -> list[OutboxEventRead]:
    return list_outbox(db, limit=limit)


@app.post("/api/v1/admin/outbox/dispatch", response_model=OutboxDispatchResult)
def dispatch_outbox_route(payload: OutboxDispatchRequest, db: DbSession) -> dict[str, int]:
    return dispatch_pending_outbox(db, limit=payload.limit)


@app.get("/api/v1/admin/metrics/summary", response_model=MetricsSummary)
def metrics_summary_route(db: DbSession) -> dict:
    return metrics_summary(db)
