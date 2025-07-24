# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY README.md .

# Entrypoint script
COPY docker_entrypoint.py ./

# Create input/output mount points
RUN mkdir -p /app/input /app/output

# No network
ENV NO_PROXY="*"

# Run the entrypoint
ENTRYPOINT ["python", "docker_entrypoint.py"] 