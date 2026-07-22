.PHONY: up down logs db-upgrade db-revision seed test lint fmt

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

db-upgrade:
	docker compose run --rm api alembic upgrade head

db-revision:
	docker compose run --rm api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose run --rm api python -m app.db.seed

collect-once:
	docker compose run --rm api python -m app.workers.run_once collect

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check app tests && uv run mypy app

fmt:
	cd backend && uv run ruff format app tests && uv run ruff check --fix app tests
