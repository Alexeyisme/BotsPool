FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY botspool-telegram/requirements.txt /tmp/requirements.txt
RUN grep -Ev "^-e ..?/botspool-shared-utils" /tmp/requirements.txt > /tmp/requirements.runtime.txt && \
    pip install --no-cache-dir -r /tmp/requirements.runtime.txt

# Install shared utils package
COPY botspool-shared-utils /tmp/botspool-shared-utils
RUN pip install --no-cache-dir /tmp/botspool-shared-utils && rm -rf /tmp/botspool-shared-utils

# Copy application code
COPY botspool-telegram /app

# Create non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8080/health')"

CMD ["python", "-m", "src.bot.main"]

