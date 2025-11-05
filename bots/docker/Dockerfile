# Multi-stage Dockerfile for 4-Bot Telegram System
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Create volume for logs
VOLUME ["/app/logs"]

# Copy all bot directories
COPY main_bot/ ./main_bot/
COPY document_bot/ ./document_bot/
COPY audio_bot/ ./audio_bot/
COPY image_bot/ ./image_bot/

# Copy bot runner script
COPY run_bots.py ./

# Expose no ports (Telegram bots are stateless)

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "run_bots.py"]
