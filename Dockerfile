# OpsGuard — Multi-stage production Dockerfile

# ── Stage 1: Builder ────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd -r opsguard && useradd -r -g opsguard -d /app -s /bin/bash opsguard

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/app"

# Copy installed packages from builder
COPY --from=builder /install /install

# Copy application code
COPY --chown=opsguard:opsguard app ./app
COPY --chown=opsguard:opsguard data ./data
COPY --chown=opsguard:opsguard alembic ./alembic
COPY --chown=opsguard:opsguard alembic.ini .
COPY --chown=opsguard:opsguard gunicorn.conf.py .

# Create necessary directories
RUN mkdir -p /app/data/chroma_db /app/data/runbooks /app/logs && \
    chown -R opsguard:opsguard /app

# Switch to non-root user
USER opsguard

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
