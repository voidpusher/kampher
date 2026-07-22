# Deploying Kampher (free tier, no cards)

Frontend is on Vercel; this wires up the backend so the public site has data.

## Stack

| Piece    | Host          | Free tier                          |
| -------- | ------------- | ---------------------------------- |
| API      | Render        | 512MB, sleeps after 15 min idle    |
| Postgres | Neon          | 0.5GB storage, serverless          |
| Vectors  | Qdrant Cloud  | 1GB cluster                        |

The API uses the `fastembed` ONNX embedder specifically so it fits in 512MB —
do not switch `KAMPHER_EMBEDDING_PROVIDER` to `local` (torch) on Render.

## 1. Neon (Postgres)

1. Sign up at https://neon.tech (GitHub login works, no card).
2. Create a project → copy the connection string
   (`postgresql://USER:PASS@HOST/neondb`).
3. Derive both driver URLs from it:
   - `KAMPHER_DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST/neondb?ssl=require`
   - `KAMPHER_DATABASE_URL_SYNC=postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require`

   Note the drivers spell SSL differently: asyncpg wants `ssl=require`,
   psycopg wants `sslmode=require`.

## 2. Qdrant Cloud (vectors)

1. Sign up at https://cloud.qdrant.io (no card for the free cluster).
2. Create a free 1GB cluster → copy the cluster URL and an API key:
   - `KAMPHER_QDRANT_URL=https://<cluster-id>.<region>.cloud.qdrant.io:6333`
   - `KAMPHER_QDRANT_API_KEY=<key>`

## 3. Render (API)

1. Push this repo to GitHub if it isn't already.
2. Sign up at https://render.com → New → Blueprint → select the repo.
   Render reads `render.yaml` and creates the `kampher-api` service.
3. In the service's Environment tab, fill in the four `sync: false`
   variables from steps 1-2.
4. Deploy. When live, note the URL (e.g. `https://kampher-api.onrender.com`).

## 4. Load the schema + data (run locally, pointed at the cloud)

Collection and embedding run from your machine against the cloud stores —
the free web service never needs to do heavy work:

```bash
cd backend
# temporarily export the cloud values (or put them in ../.env)
export KAMPHER_DATABASE_URL="postgresql+asyncpg://...?ssl=require"
export KAMPHER_DATABASE_URL_SYNC="postgresql+psycopg://...?sslmode=require"
export KAMPHER_QDRANT_URL="https://....cloud.qdrant.io:6333"
export KAMPHER_QDRANT_API_KEY="..."
unset KAMPHER_QDRANT_PATH   # cloud, not embedded

uv run alembic upgrade head
uv run python -m app.db.seed
uv run python -m app.workers.run_once collect
uv run python -m app.workers.run_once embed
```

## 5. Point Vercel at the API

In the Vercel project → Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=https://kampher-api.onrender.com
```

Redeploy the frontend. Done — the public site now serves live data.

## Refreshing data

The `Near-real-time production refresh` GitHub Actions workflow collects public
sources every 15 minutes, refreshes Stack Overflow every two hours, and runs a
bounded intelligence pass daily. It can also be started manually. Add these repository secrets in
GitHub under **Settings -> Secrets and variables -> Actions**:

- `KAMPHER_DATABASE_URL`
- `KAMPHER_DATABASE_URL_SYNC`
- `KAMPHER_QDRANT_URL`
- `KAMPHER_QDRANT_API_KEY`
- `GEMINI_API_KEY` (enrichment, opportunities, and trends)

To enable the Reddit collector, also add:

- `KAMPHER_REDDIT_CLIENT_ID`
- `KAMPHER_REDDIT_CLIENT_SECRET`

The workflow applies pending migrations, collects only source items that have
not already been stored, upserts search vectors, enriches a bounded daily batch,
then clusters pain and publishes eligible opportunities. Collection is cursor-based
and both database writes and Qdrant upserts are idempotent.

The Render service only serves queries; the scheduled job performs the heavier
collection and embedding work.
