# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config.yaml .

# Create logs directory
RUN mkdir -p logs state

# Set Python path
ENV PYTHONPATH=/workspace/src:$PYTHONPATH

# Set working directory for running
WORKDIR /workspace

# Default command
CMD ["python", "-m", "bot.main", "--mode", "dry-run", "--config", "config.yaml"]