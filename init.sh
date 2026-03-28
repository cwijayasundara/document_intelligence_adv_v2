#!/bin/bash
set -euo pipefail

echo "=== Bootstrapping dev environment ==="

# Backend dependencies
cd backend && uv sync && cd ..

# Frontend dependencies
cd frontend && npm ci && cd ..

# Environment
if [ -f "backend/.env.example" ] && [ ! -f "backend/.env" ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from .env.example — add your API keys"
fi

# Docker services
docker compose up -d --build

# Health checks
echo "Waiting for services..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "Backend is healthy"
    break
  fi
  echo "Waiting for backend... ($i/10)"
  sleep 2
done

for i in $(seq 1 10); do
  if curl -sf http://localhost:5173 > /dev/null 2>&1; then
    echo "Frontend is healthy"
    break
  fi
  echo "Waiting for frontend... ($i/10)"
  sleep 2
done

echo "=== Environment ready ==="
