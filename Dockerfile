# ==============================================================================
# HS AI SOLUTIONS - JULY CLOUD AI DOCKERFILE
# Production Docker Container for Render CPU Inference
# Founder: Harshan Seliyan
# ==============================================================================

FROM python:3.11-slim-bookworm

# Set container environment flags
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    MODELS_DIR=/models \
    MODEL_PATH=/models/Gravity_HS.gguf \
    CMAKE_ARGS="-DGGML_BLAS=OFF"

# Install essential system build tools for llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create working directory and persistent mount directory
WORKDIR /app
RUN mkdir -p /models && chmod 777 /models

# Copy dependency definition
COPY requirements.txt .

# Install dependencies with pre-compiled wheels where possible
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Health check probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python scripts/health_check.py http://localhost:${PORT} || exit 1

# Expose dynamic HTTP port
EXPOSE 8000

# Execute FastAPI via Uvicorn with single worker to conserve CPU/RAM
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
