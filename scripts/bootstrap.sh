#!/usr/bin/env bash
# One-shot local bootstrap: infra up, schema migrated, taxonomy seeded.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">> Created .env from .env.example — add your ANTHROPIC_API_KEY before enriching."
fi

docker compose up -d --build postgres redis qdrant api
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.db.seed
docker compose up -d

echo ">> Kampher is up:"
echo "   API      http://localhost:8000/docs"
echo "   Frontend http://localhost:3000"
echo "   Qdrant   http://localhost:6333/dashboard"
echo ">> First data: docker compose run --rm api python -m app.workers.run_once collect"
