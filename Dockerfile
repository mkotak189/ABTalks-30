# ============================================================
# STAGE 1: BUILDER (install dependencies)
# ============================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (if you have one)
# For now, we'll install from pip directly in final stage
# But if you want a requirements.txt:
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# STAGE 2: FINAL (slim runtime)
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder (if using multi-stage pip)
# For simplicity, install directly in final stage
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-dotenv \
    openai \
    pydantic \
    langchain \
    langchain-anthropic \
    boto3 \
    requests \
    tiktoken \
    presidio-analyzer \
    presidio-anonymizer \
    crewai \
    mcp

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "coverage-chatbot-api.main:app", "--host", "0.0.0.0", "--port", "8000"]