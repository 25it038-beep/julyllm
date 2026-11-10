# HS AI SOLUTIONS — PRODUCTION DOCKERFILE
# Service: July Distribution Backend
# Founder: Harshan Seliyan

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY july_distribution/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY july_distribution /app/july_distribution

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn july_distribution.server.main:app --host 0.0.0.0 --port ${PORT}"]
