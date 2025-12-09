# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/chroma_db

# Ensure all package directories exist and have __init__.py
RUN mkdir -p /app/app/models /app/app/api /app/app/core /app/app/schemas /app/app/services && \
    touch /app/app/__init__.py \
    /app/app/models/__init__.py \
    /app/app/api/__init__.py \
    /app/app/core/__init__.py \
    /app/app/schemas/__init__.py \
    /app/app/services/__init__.py

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
