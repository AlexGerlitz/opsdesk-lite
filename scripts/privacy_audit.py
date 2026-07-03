from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
FORBIDDEN = [
    "auto" + "school",
    "авто" + "школ",
    "chat" + "_id",
    "telegram" + "_id",
    "admin" + "_url",
    "private" + " token",
    "bearer" + " ",
]
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)")


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def main() -> int:
    errors: list[str] = []
    for path in iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for forbidden in FORBIDDEN:
            if forbidden in lower:
                errors.append(f"{path.relative_to(ROOT)} contains forbidden marker: {forbidden}")
        if PHONE_RE.search(text):
            errors.append(f"{path.relative_to(ROOT)} contains a phone-like value")
    if errors:
        print("privacy audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("privacy audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
