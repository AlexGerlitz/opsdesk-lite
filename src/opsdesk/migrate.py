from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from opsdesk.database import engine

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def main() -> int:
    scripts = sorted(MIGRATIONS.glob("*.sql"))
    if not scripts:
        raise SystemExit("no migrations found")
    with engine.begin() as conn:
        for script in scripts:
            sql = script.read_text(encoding="utf-8")
            for statement in [chunk.strip() for chunk in sql.split(";") if chunk.strip()]:
                conn.execute(text(statement))
            print(f"applied {script.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
