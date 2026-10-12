.PHONY: dev backend frontend worker scheduler maintenance test lint metadata-import validation generate-api analyze

dev:
	docker compose up --build

backend:
	cd backend && RUN_EMBEDDED_WORKER=false .venv/bin/uvicorn app.main:app --reload

frontend:
	npm --prefix frontend run dev

worker:
	cd backend && .venv/bin/python -m app.worker

scheduler:
	cd backend && .venv/bin/python -m app.scheduler

maintenance:
	cd backend && .venv/bin/python -m app.maintenance

test:
	cd backend && .venv/bin/python -m pytest -q

lint:
	cd backend && .venv/bin/python -m ruff check app tests
	npm --prefix frontend run lint

metadata-import:
	cd backend && .venv/bin/python tools/import_stock_metadata.py --refresh

validation:
	cd backend && .venv/bin/python tools/validate_stock_apis.py

generate-api:
	npm --prefix frontend run generate:api

analyze:
	npm --prefix frontend run analyze
