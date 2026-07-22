# Kampher

> Discover what people need before they search for a solution.

Kampher is an AI-powered **Opportunity Intelligence Platform**. It continuously ingests
conversations from the public internet (Reddit, X, GitHub, Hacker News, …), runs every
document through a 15-stage AI enrichment pipeline, clusters pain into problems, connects
everything in a knowledge graph, and produces **ranked, explained startup opportunities**.

Kampher includes a near-real-time incremental scraper; data is the fuel and the
reasoning layer turns that live corpus into product intelligence.

---

## System overview

```
 Collectors ──► Cleaning ──► Enrichment (15-stage AI pipeline) ──► Embeddings
     │                                                                 │
     ▼                                                                 ▼
 PostgreSQL ◄──────────── Knowledge Graph ◄──────────────────────── Qdrant
     │                                                                 │
     └──────────────► Intelligence Engine (opportunities, trends) ◄────┘
                                      │
                                      ▼
                              FastAPI REST API
                                      │
                                      ▼
                              Next.js frontend
```

Full design rationale: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Stack

| Layer          | Technology                                              |
| -------------- | ------------------------------------------------------- |
| API            | FastAPI, Pydantic v2                                     |
| Persistence    | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic           |
| Vectors        | Qdrant                                                   |
| Queues/Agents  | Celery + Redis, dedicated queues per agent               |
| AI             | Google Gemini (structured outputs), FastEmbed                |
| Frontend       | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, Framer Motion |
| Infra          | Docker Compose, GitHub Actions CI                        |

## Quickstart

```bash
cp .env.example .env          # fill in GEMINI_API_KEY (+ optional source API keys)
make up                       # postgres, redis, qdrant, api, workers, beat, frontend
make db-upgrade               # apply migrations
make seed                     # taxonomy seed (industries, topics)
```

- API: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Qdrant dashboard: http://localhost:6333/dashboard

### Local development (no Docker for the app itself)

```bash
# backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.api.main:app --reload

# one incremental scrape: collect and embed only newly discovered posts
uv run python -m app.workers.run_once refresh

# workers (each agent = a queue; run one or many)
uv run celery -A app.workers.celery_app worker -Q collect,enrich,embed,intelligence -l info
uv run celery -A app.workers.celery_app beat -l info

# frontend
cd frontend
npm install && npm run dev
```

## Repository layout

```
backend/
  app/
    api/            # FastAPI routers + dependency wiring
    core/           # config, logging, errors
    db/             # engine, sessions, base metadata
    models/         # SQLAlchemy 2.0 typed models
    schemas/        # Pydantic DTOs (API + internal contracts)
    repositories/   # data access (repository pattern)
    services/       # business logic
    collectors/     # source-plugin framework + Reddit/X/GitHub/HN collectors
    ai/             # LLM clients, embeddings, 15-stage pipeline, scoring
    vector/         # Qdrant collections + semantic/hybrid search
    graph/          # knowledge graph service (Postgres property graph)
    workers/        # Celery app, queues, agent tasks, beat schedule
  alembic/          # migrations
  tests/
frontend/           # Next.js app
scripts/            # operational scripts (bootstrap)
docs/               # architecture docs
.github/workflows/  # CI
docker-compose.yml  # postgres, redis, qdrant, api, workers, beat, frontend
```

## The agents

| Agent              | Queue          | Responsibility                                        |
| ------------------ | -------------- | ----------------------------------------------------- |
| Collector Agent    | `collect`      | Pull new documents from every registered source        |
| Cleaner Agent      | `clean`        | Dedup, normalize, language/spam gate                  |
| Embedding Agent    | `embed`        | Vectorize documents + clusters into Qdrant            |
| Trend Agent        | `intelligence` | Time-series scoring of topics/problems                |
| Opportunity Agent  | `intelligence` | Cluster pain → generate + score opportunities          |
| Research Agent     | `intelligence` | Competitor/market context for opportunities           |
| Report Agent       | `reports`      | Full opportunity reports                              |
| Alert Agent        | `alerts`       | Watch saved queries, notify on spikes                 |

## Testing

```bash
cd backend && uv run pytest          # unit + service tests
cd frontend && npm run lint && npm run build
```

CI runs lint (ruff), type-check (mypy), tests, and frontend build on every push.

Production collection is near-real-time and source-aware: public feeds refresh every
15 minutes, while Stack Overflow refreshes every two hours to respect its anonymous API
quota. Cursors, deduplication, and incremental vector upserts prevent repeat processing.
