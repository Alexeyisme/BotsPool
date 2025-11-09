#!/bin/bash
# BotsPool Gateway Startup Script

set -e

echo "🚀 Starting BotsPool Gateway..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
required_vars=("DATABASE_URL" "REDIS_URL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

# Create logs directory
mkdir -p logs

# Start the application
echo "🔧 Starting BotsPool Gateway on port ${PORT:-8000}..."

if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "🏭 Running in production mode"
    exec python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-4}
else
    echo "🔧 Running in development mode with hot reload"
    exec python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi
