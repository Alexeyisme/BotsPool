#!/bin/bash
set -e

echo "Starting BotsPool Infrastructure..."
docker-compose -f docker-compose.infrastructure.yml up -d

echo "Waiting for services to be healthy..."
sleep 10

echo "Infrastructure ready!"
echo "  - PostgreSQL Gateway: localhost:5432"
echo "  - PostgreSQL ToDo Graph: localhost:5433"
echo "  - Redis: localhost:6379"
echo ""
echo "To start services:"
echo "  Gateway: cd botspool-gateway && docker-compose up"
echo "  ToDo Graph: cd botspool-todo-graph && docker-compose up"
