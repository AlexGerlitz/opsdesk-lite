from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opsdesk.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TicketPriority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class TicketStatus(StrEnum):
    new = "new"
    triaged = "triaged"
    waiting_customer = "waiting_customer"
    resolved = "resolved"


OPEN_STATUSES = {
    TicketStatus.new,
    TicketStatus.triaged,
    TicketStatus.waiting_customer,
}


def default_sla_due_at() -> datetime:
    return utcnow() + timedelta(hours=4)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_ref: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    requester_name: Mapped[str] = mapped_column(String(120))
    requester_email: Mapped[str] = mapped_column(String(160), index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True)
    subject: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False),
        default=TicketPriority.normal,
        index=True,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False), default=TicketStatus.new, index=True
    )
    assignee: Mapped[str | None] = mapped_column(String(120))
    sla_due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_sla_due_at
    )
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    activities: Mapped[list[ActivityLog]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="ActivityLog.id"
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="activities")
