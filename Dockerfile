# ImpactFlow API — build from monorepo root (Railway / Docker).
# Context: repository root. Used by railway.toml.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .

ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV DEBUG=false

EXPOSE 8000

# Railway injects PORT; local/docker default to 8000.
CMD ["sh", "-c", "python -m app.scripts.preflight_db && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
