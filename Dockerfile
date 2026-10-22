# syntax=docker/dockerfile:1
# EduWell Analytics - Production Multi-Stage Container

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8000

# Install minimal OS dependencies for health check and numerical wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=appuser:appgroup . /app/

# Ensure workspace and temp directory permissions
RUN mkdir -p /tmp/eduwell && chown -R appuser:appgroup /tmp/eduwell /app

USER appuser

EXPOSE 8000

# Container liveness/readiness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

# Production server command with reverse-proxy header support
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--workers", "1"]
