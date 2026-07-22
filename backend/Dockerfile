FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /srv/kampher

# Dependency layer (cached unless pyproject/lock changes)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

ENV PATH="/srv/kampher/.venv/bin:$PATH"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
