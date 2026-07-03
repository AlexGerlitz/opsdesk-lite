from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_openapi_exposes_recruiter_relevant_backend_surface(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/tickets" in paths
    assert "/api/v1/intake/webhook" in paths
    assert "/api/v1/operator/queue" in paths
    assert "/api/v1/admin/sla/scan" in paths


def test_public_files_do_not_reference_private_customer_data():
    forbidden = [
        "auto" + "school",
        "авто" + "школ",
        "chat" + "_id",
        "telegram" + "_id",
        "admin" + "_url",
        "bearer" + " ",
    ]
    for path in ROOT.rglob("*"):
        if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in forbidden:
            assert marker not in text, f"{path.relative_to(ROOT)} contains {marker}"
