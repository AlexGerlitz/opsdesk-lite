from __future__ import annotations

import argparse
from datetime import UTC, datetime

import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from opsdesk.config import get_settings
from opsdesk.database import SessionLocal
from opsdesk.models import OPEN_STATUSES, ActivityLog, Ticket


def redis_client():
    try:
        return redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
    except Exception:
        return None


def scan_sla(db: Session, *, now: datetime | None = None, redis_conn=None) -> dict[str, int | bool]:
    current_time = now or datetime.now(UTC)
    candidates = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.status.in_(OPEN_STATUSES))
            .where(Ticket.sla_breached.is_(False))
            .where(Ticket.sla_due_at < current_time)
        )
    )
    published = False
    for ticket in candidates:
        ticket.sla_breached = True
        db.add(
            ActivityLog(
                ticket=ticket,
                event_type="sla_breached",
                actor="sla_worker",
                note=f"SLA due at {ticket.sla_due_at.isoformat()}",
            )
        )
        if redis_conn is not None:
            try:
                redis_conn.xadd(
                    "opsdesk:sla_events",
                    {"ticket_id": ticket.id, "event": "sla_breached"},
                )
                published = True
            except Exception:
                published = False
    db.commit()
    return {
        "scanned": len(candidates),
        "breached": len(candidates),
        "redis_event_published": published,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpsDesk SLA worker.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    parser.parse_args()

    with SessionLocal() as db:
        result = scan_sla(db, redis_conn=redis_client())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
