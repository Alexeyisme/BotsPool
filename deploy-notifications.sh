#!/bin/bash

# BotsPool Notification Service Deployment Script

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔔 BotsPool Notification Service Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if .env.docker exists in notification service
if [ ! -f "botspool-notification-service/.env.docker" ]; then
    echo "⚠️  Creating .env.docker from sample..."
    cp botspool-notification-service/env.sample botspool-notification-service/.env.docker
    
    # Generate API key
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update API key in all services
    echo "🔑 Generated API key: $API_KEY"
    sed -i.bak "s/dev-secret-key-change-in-production/$API_KEY/g" botspool-notification-service/.env.docker
    
    echo ""
    echo "⚠️  IMPORTANT: Add the following to your .env.docker files:"
    echo ""
    echo "   botspool-telegram/.env.docker:"
    echo "   NOTIFICATION_PORT=8081"
    echo "   NOTIFICATION_API_KEY=$API_KEY"
    echo ""
    echo "   botspool-todo-graph/.env.docker:"
    echo "   NOTIFICATION_SERVICE_URL=http://botspool-notification-service:8090"
    echo "   NOTIFICATION_API_KEY=$API_KEY"
    echo ""
    read -p "Press Enter after updating .env.docker files..."
fi

echo "📦 Step 1: Building notification service..."
cd botspool-notification-service
docker compose build
echo "✅ Build complete"
echo ""

echo "📦 Step 2: Rebuilding Telegram bot (with notification endpoint)..."
cd ../botspool-telegram
docker compose up -d --build
echo "✅ Bot rebuilt"
echo ""

echo "📦 Step 3: Rebuilding ToDo agent (with notification tools)..."
cd ../botspool-todo-graph
docker compose up -d --build
echo "✅ Agent rebuilt"
echo ""

echo "🚀 Step 4: Starting notification service..."
cd ../botspool-notification-service
docker compose up -d
echo "✅ Notification service started"
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to be ready (10 seconds)..."
sleep 10

echo "🏥 Step 5: Health checks..."
echo ""

echo "Notification Service:"
curl -s http://localhost:8090/health | jq . || echo "  ❌ Not responding"
echo ""

echo "Telegram Bot (notification endpoint):"
curl -s http://localhost:8081/health | jq . || echo "  ❌ Not responding"
echo ""

echo "ToDo Agent:"
curl -s http://localhost:8011/health | jq . || echo "  ❌ Not responding"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Running Services:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "botspool-(notification|telegram|todo)" || echo "No services found"
echo ""
echo "🧪 Test the notification system:"
echo ""
echo "1. Message your bot in Telegram:"
echo "   'Send me a test notification'"
echo ""
echo "2. Or schedule a reminder:"
echo "   'Remind me in 2 minutes to check this'"
echo ""
echo "3. View logs:"
echo "   docker logs -f botspool-notification-service"
echo "   docker logs -f botspool-notification-worker"
echo ""
echo "📚 Documentation:"
echo "   - README: botspool-notification-service/README.md"
echo "   - Integration: botspool-notification-service/INTEGRATION.md"
echo "   - Deployment: botspool-notification-service/DEPLOYMENT.md"
echo ""

