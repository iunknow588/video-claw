FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./pyproject.toml
COPY src ./src
RUN pip install --no-cache-dir .

# Prepare runtime directories
RUN mkdir -p /app/runtime/logs /app/runtime/media

# Run application
CMD ["uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
