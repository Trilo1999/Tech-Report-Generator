FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies required for build tools, PostgreSQL client, and font utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and application assets
COPY src/ ./src/
COPY data/sample_data/ ./data/sample_data/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pytest.ini .

# Create directory for reports and local state
RUN mkdir -p /app/reports /app/data/qdrant_storage

EXPOSE 8000

CMD ["uvicorn", "src.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
