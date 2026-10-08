# ==========================================
# TensorForge 2.0 - Phase 2 Dockerfile
# ==========================================
# Contract requirement:
# Single command run: docker run -p 8000:8000 -e API_KEY=<key> <image>
# Must NOT need internet access at runtime (bundle all weights/dependencies).
# GET /health must return 200 within 120s of start.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ backend/

# Copy trained ML model artifacts (required at runtime)
COPY ml/artifacts/ ml/artifacts/

# Copy pre-built React frontend
COPY frontend/dist/ frontend/dist/

# Copy schemas for validation
COPY schemas/ schemas/

# Copy .env.example as fallback (actual API_KEY comes from -e flag)
COPY .env.example .env.example

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

# Expose service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
