# Use official slim Python 3.12 image for a small footprint and security
FROM python:3.12-slim

# Prevent Python from writing .pyc files to disk and ensure output is sent straight to stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root user and group for security best practices
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY main.py commands.py utils.py README.md MONETIZATION.md ./
COPY assets/ ./assets/

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Cloud Run injects the PORT env var; default to 8080 for local builds
ENV PORT=8080
EXPOSE ${PORT}

# Default command to run the Telegram bot
CMD ["python", "main.py"]
