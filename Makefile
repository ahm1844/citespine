.PHONY: up down api install ingest index eval lint test

up:
	docker compose up -d

down:
	docker compose down

api:
	docker compose up -d api

install:
	pip install -r requirements.txt || true

ingest:
	docker compose run --rm api python -m src.ingest.runner

index:
	docker compose run --rm api python -m src.index.build_index

eval:
	docker compose run --rm api python -m src.eval.evaluate || true

lint:
	ruff check . ; black --check . ; mypy || true

test:
	pytest -q

label_add:
	docker compose run --rm api python -m src.eval.label add $(Q) $(C)
label_remove:
	docker compose run --rm api python -m src.eval.label remove $(Q) $(C)