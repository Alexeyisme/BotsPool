#!/bin/bash
# BotsPool Gateway Health Check Script

set -e

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-10}"

echo "🏥 Checking BotsPool Gateway health..."

# Check basic health endpoint
echo "📊 Checking basic health..."
if curl -f -s --max-time $TIMEOUT "$GATEWAY_URL/health" > /dev/null; then
    echo "✅ Basic health check passed"
else
    echo "❌ Basic health check failed"
    exit 1
fi

# Check detailed status
echo "📊 Checking detailed status..."
if curl -f -s --max-time $TIMEOUT "$GATEWAY_URL/health/status" > /dev/null; then
    echo "✅ Detailed status check passed"
else
    echo "❌ Detailed status check failed"
    exit 1
fi

# Check readiness probe
echo "📊 Checking readiness..."
if curl -f -s --max-time $TIMEOUT "$GATEWAY_URL/health/ready" > /dev/null; then
    echo "✅ Readiness check passed"
else
    echo "❌ Readiness check failed"
    exit 1
fi

# Check liveness probe
echo "📊 Checking liveness..."
if curl -f -s --max-time $TIMEOUT "$GATEWAY_URL/health/live" > /dev/null; then
    echo "✅ Liveness check passed"
else
    echo "❌ Liveness check failed"
    exit 1
fi

echo "🎉 All health checks passed!"
