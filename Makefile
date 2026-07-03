.PHONY: install test lint smoke replay run docker-up docker-down migrate worker privacy-audit

install:
	python3 -m pip install ".[dev]"

test:
	pytest -q

lint:
	ruff check .

smoke:
	python3 scripts/smoke.py

replay:
	python3 scripts/reviewer_replay.py

run:
	uvicorn opsdesk.main:app --reload

migrate:
	python3 -m opsdesk.migrate

worker:
	python3 -m opsdesk.worker --once

privacy-audit:
	python3 scripts/privacy_audit.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
