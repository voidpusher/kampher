# Kampher recovery runbook

Kampher's durable source of truth is Neon Postgres. Qdrant is a derived search index
and can be rebuilt from Postgres, so it must never be used as the only copy of data.

## Current protection

- Neon `production` has a six-hour point-in-time restore window.
- A non-expiring manual snapshot was captured on 2026-08-25 at 08:09:56 UTC.
- GitHub Actions checks recovery readiness daily and opens an assigned issue on failure.
- Alembic migrations in the repository are the authoritative schema history.

The manual snapshot is a stable disaster-recovery baseline. The rolling Neon history
is the preferred recovery source for recent accidental writes or schema changes.

## Recovery procedure

1. Stop scheduled ingestion by disabling `Near-real-time production refresh` in
   GitHub Actions. Do not delete the workflow or credentials.
2. In Neon, open `kampher` → `production` → **Backup & Restore**.
3. For a recent incident, choose a timestamp inside the six-hour window and use
   **Preview data** first. For older damage, select the non-expiring snapshot.
4. Confirm the preview contains `posts`, `source_cursors`, `industries`, and
   `alembic_version`, then restore `production`.
5. Wait for Neon to finish before reconnecting the API. A restore can briefly interrupt
   database connections, but the production connection string remains stable.
6. Run `python -m app.workers.run_once recovery` with the production environment.
7. Rebuild the derived vector index with `python -m app.workers.run_once embed`.
8. Verify `/health/ready`, `/health/data`, search, and one evidence-backed chat answer.
9. Re-enable the scheduled refresh only after all checks pass.

Never test a restore by overwriting `production`. Use Neon's preview-data flow or a
temporary branch. A real production restore is reserved for an actual incident and
must be followed by the checks above.
