from __future__ import annotations

import json
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from opsdesk.database import Base, get_db
from opsdesk.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)


@contextmanager
def _client_with_temp_db(db_path: Path) -> Generator[TestClient, None, None]:
    from fastapi.testclient import TestClient

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def run_replay() -> dict[str, Any]:
    with TemporaryDirectory() as tmp_dir:
        with _client_with_temp_db(Path(tmp_dir) / "reviewer.db") as client:
            return _run_replay_with_client(client)


def _run_replay_with_client(client: TestClient) -> dict[str, Any]:
    health = client.get("/health").json()
    webhook_payload = {
        "source": "crm_mock",
        "payload_id": "lead-1001",
        "requester_name": "Synthetic User",
        "requester_email": "synthetic@example.test",
        "text": "Need help because the payment status did not update in the admin queue.",
        "priority": "high",
    }
    created = client.post("/api/v1/intake/webhook", json=webhook_payload).json()
    duplicate = client.post("/api/v1/intake/webhook", json=webhook_payload).json()
    queue = client.get("/api/v1/operator/queue").json()
    updated = client.patch(
        f"/api/v1/tickets/{created['id']}/status",
        json={
            "status": "triaged",
            "actor": "reviewer",
            "note": "validated intake and backend state",
            "assignee": "api-operator",
        },
    ).json()
    outbox_before = client.get("/api/v1/admin/outbox").json()
    dispatch = client.post("/api/v1/admin/outbox/dispatch", json={"limit": 10}).json()
    metrics = client.get("/api/v1/admin/metrics/summary").json()
    openapi = client.get("/openapi.json").json()
    selected_paths = [
        path
        for path in openapi["paths"]
        if path
        in {
            "/api/v1/tickets",
            "/api/v1/intake/webhook",
            "/api/v1/operator/queue",
            "/api/v1/admin/outbox/dispatch",
            "/api/v1/admin/metrics/summary",
        }
    ]

    checks = {
        "health_ok": health["status"] == "ok",
        "idempotent_webhook": duplicate["id"] == created["id"],
        "queue_contains_ticket": any(item["id"] == created["id"] for item in queue),
        "status_handoff_triaged": updated["status"] == "triaged",
        "assignee_recorded": updated["assignee"] == "api-operator",
        "outbox_written_once": len(outbox_before) == 1,
        "outbox_dispatched": dispatch == {"scanned": 1, "sent": 1, "failed": 0},
        "metrics_total_tickets": metrics["total_tickets"] == 1,
        "openapi_paths_present": len(selected_paths) == 5,
    }

    return {
        "scenario": (
            "webhook intake -> idempotent backend state -> operator queue -> "
            "status handoff -> outbox dispatch -> metrics -> OpenAPI contract"
        ),
        "checks": checks,
        "ticket": {
            "id": created["id"],
            "external_ref": created["external_ref"],
            "priority": created["priority"],
            "status_after_handoff": updated["status"],
            "activity_events": [activity["event_type"] for activity in updated["activities"]],
        },
        "queue_size": len(queue),
        "outbox_dispatch": dispatch,
        "metrics": {
            "total_tickets": metrics["total_tickets"],
            "open_tickets": metrics["open_tickets"],
            "by_status": metrics["by_status"],
            "by_priority": metrics["by_priority"],
            "by_channel": metrics["by_channel"],
            "outbox_by_status": metrics["outbox_by_status"],
        },
        "openapi_paths": selected_paths,
    }


def main() -> int:
    result = run_replay()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
