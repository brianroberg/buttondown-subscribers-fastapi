# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.12-slim as builder

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies to user site-packages
RUN pip install --user --no-cache-dir --upgrade -r requirements.txt

# Pre-compile Python code for faster startup
COPY ./app /tmp/app
RUN python -m compileall /tmp/app

# ============================================
# Stage 2: Runtime - Production image
# ============================================
FROM python:3.12-slim as runtime

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy pre-compiled application
COPY --from=builder /tmp/app /app

# Create non-root user and data directory
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

# Environment configuration
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/app.db

USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=2)"

# Shell form for $PORT substitution (Cloud Run)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
