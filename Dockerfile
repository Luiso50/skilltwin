# Multi-stage build for smaller image
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN groupadd -r skilltwin && useradd -r -g skilltwin -d /app -s /sbin/nologin skilltwin

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy application code
COPY . .

# Set permissions
RUN chown -R skilltwin:skilltwin /app

# Production stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN groupadd -r skilltwin && useradd -r -g skilltwin -d /app -s /sbin/nologin skilltwin

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app

# Switch to non-root user
USER skilltwin

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

EXPOSE 8000

WORKDIR /app/cerebro

CMD ["python", "server.py"]
