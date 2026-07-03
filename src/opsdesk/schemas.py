from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opsdesk.models import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    requester_name: str = Field(min_length=2, max_length=120)
    requester_email: str = Field(min_length=5, max_length=160)
    channel: str = Field(min_length=2, max_length=40)
    subject: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=10, max_length=4000)
    priority: TicketPriority = TicketPriority.normal
    external_ref: str | None = Field(default=None, max_length=80)

    @field_validator("requester_email")
    @classmethod
    def email_must_look_like_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("requester_email must look like an email address")
        return value.lower()

    @field_validator("channel")
    @classmethod
    def channel_is_simple(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("_", "").replace("-", "").isalnum():
            raise ValueError("channel must be a simple source label")
        return normalized


class WebhookTicket(BaseModel):
    source: str = Field(min_length=2, max_length=40)
    payload_id: str = Field(min_length=4, max_length=80)
    requester_name: str = Field(min_length=2, max_length=120)
    requester_email: str = Field(min_length=5, max_length=160)
    text: str = Field(min_length=10, max_length=4000)
    priority: TicketPriority = TicketPriority.normal


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    actor: str = Field(default="operator", min_length=2, max_length=120)
    note: str = Field(default="", max_length=1000)
    assignee: str | None = Field(default=None, max_length=120)


class ActivityCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=80)
    actor: str = Field(default="operator", min_length=2, max_length=120)
    note: str = Field(default="", max_length=1000)


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    event_type: str
    actor: str
    note: str
    created_at: datetime


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: str | None
    requester_name: str
    requester_email: str
    channel: str
    subject: str
    message: str
    priority: TicketPriority
    status: TicketStatus
    assignee: str | None
    sla_due_at: datetime
    sla_breached: bool
    created_at: datetime
    updated_at: datetime
    activities: list[ActivityRead] = Field(default_factory=list)


class QueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    priority: TicketPriority
    status: TicketStatus
    assignee: str | None
    sla_due_at: datetime
    sla_breached: bool
    created_at: datetime


class SlaScanResult(BaseModel):
    scanned: int
    breached: int
    redis_event_published: bool
