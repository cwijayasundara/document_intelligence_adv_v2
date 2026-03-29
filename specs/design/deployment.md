# Deployment Architecture — PE Document Intelligence Platform

**Version:** 1.0
**Date:** 2026-03-28

---

## 1. Deployment Model

This is an R&D / internal tool project. There is no production deployment, no CI/CD pipeline, no cloud infrastructure, and no uptime SLA. The platform runs entirely on a developer workstation.

```
Developer Workstation
|
+-- Native Processes
|   +-- Backend:  Python 3.13, uvicorn (port 8000)
|   +-- Frontend: Node.js, Vite dev server (port 5173)
|
+-- Docker Compose
|   +-- PostgreSQL 16 (port 5432)
|   +-- Weaviate latest (port 8080, gRPC 50051)
|
+-- External APIs (HTTPS outbound)
    +-- Reducto Cloud API
    +-- OpenAI API
```

---

## 2. Docker Compose Services

### docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16
    container_name: doc_intel_postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: doc_intel
      POSTGRES_USER: doc_intel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-doc_intel_dev}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U doc_intel"]
      interval: 5s
      timeout: 5s
      retries: 5

  weaviate:
    image: semitechnologies/weaviate:latest
    container_name: doc_intel_weaviate
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      DEFAULT_VECTORIZER_MODULE: "text2vec-openai"
      ENABLE_MODULES: "text2vec-openai"
      OPENAI_APIKEY: ${OPENAI_API_KEY}
    volumes:
      - weaviate_data:/var/lib/weaviate

volumes:
  pgdata:
  weaviate_data:
```

**Why Docker for databases only:** Fast iteration with hot reload (uvicorn --reload, Vite HMR) without Docker image rebuild cycles. Databases benefit from Docker for consistent environments, data isolation, and easy teardown.

---

## 3. Local Development Servers

### Backend (FastAPI + Uvicorn)

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- **Hot reload:** `--reload` watches `src/` for changes
- **Python version:** 3.13 (managed via pyenv or system Python)
- **Virtual environment:** Standard venv in `backend/.venv/`

### Frontend (Vite)

```bash
cd frontend
npm run dev
```

- **Port:** 5173 (Vite default)
- **HMR:** Instant module replacement
- **Proxy:** Vite config proxies `/api` to `http://localhost:8000` to avoid CORS during development

### Vite Proxy Configuration

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

---

## 4. Environment Management

### .env file (root and backend)

```bash
# API Keys
OPENAI_API_KEY=sk-...
REDUCTO_API_KEY=...

# Database
DATABASE_URL=postgresql+asyncpg://doc_intel:doc_intel_dev@localhost:5432/doc_intel
POSTGRES_PASSWORD=doc_intel_dev

# Weaviate
WEAVIATE_URL=http://localhost:8080

# Model
OPENAI_MODEL=gpt-5.4-mini
```

### config.yml (backend)

```yaml
storage:
  upload_dir: "./data/upload"
  parsed_dir: "./data/parsed"
  schemas_dir: "./schemas"

chunking:
  max_tokens: 512
  overlap_tokens: 100

bulk:
  concurrent_documents: 10
  max_retries: 3
  retry_delay_seconds: 30

rag:
  default_search_mode: "hybrid"
  default_alpha: 0.5
  top_k: 5
```

### Priority

1. Environment variables (`.env`) for secrets and connection strings
2. `config.yml` for application behavior configuration
3. Pydantic Settings merges both sources with env vars taking precedence

---

## 5. Bootstrap Script (init.sh)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== PE Document Intelligence Platform - Bootstrap ==="

# 1. Create data directories
echo "Creating data directories..."
mkdir -p data/upload data/parsed data/schemas

# 2. Copy .env if not exists
if [ ! -f .env ]; then
  echo "Creating .env from template..."
  cp .env.example .env
  echo "IMPORTANT: Edit .env with your API keys before starting."
fi

# 3. Start Docker services
echo "Starting PostgreSQL and Weaviate..."
docker compose up -d
echo "Waiting for PostgreSQL to be ready..."
until docker compose exec -T postgres pg_isready -U doc_intel 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready."

# 4. Backend setup
echo "Setting up backend..."
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "Running database migrations..."
alembic upgrade head
cd ..

# 5. Frontend setup
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "To start the backend:  cd backend && source .venv/bin/activate && uvicorn src.main:app --reload --port 8000"
echo "To start the frontend: cd frontend && npm run dev"
```

---

## 6. Database Migrations (Alembic)

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current migration state
alembic current
```

Alembic connects to PostgreSQL using the `DATABASE_URL` from `.env`.

---

## 7. Port Allocation

| Service | Port | Protocol |
|---------|------|----------|
| FastAPI backend | 8000 | HTTP |
| Vite frontend | 5173 | HTTP |
| PostgreSQL | 5432 | TCP |
| Weaviate HTTP | 8080 | HTTP |
| Weaviate gRPC | 50051 | gRPC |

---

## 8. Data Persistence

| Data | Storage | Persistence |
|------|---------|-------------|
| PostgreSQL data | Docker volume `pgdata` | Survives container restart; lost on `docker compose down -v` |
| Weaviate data | Docker volume `weaviate_data` | Survives container restart; lost on `docker compose down -v` |
| Uploaded files | `data/upload/` (local filesystem) | Persistent until manually deleted |
| Parsed files | `data/parsed/` (local filesystem) | Persistent until manually deleted |
| YAML schemas | `data/schemas/` (local filesystem) | Persistent until manually deleted |

---

## 9. Teardown

```bash
# Stop services, keep data
docker compose down

# Stop services and delete all data (DESTRUCTIVE)
docker compose down -v
rm -rf data/upload/* data/parsed/* data/schemas/*
```

---

## 10. No CI/CD

This is an R&D project. There is no:

- Continuous integration pipeline
- Automated testing on push
- Staging or production environment
- Container registry
- Deployment automation
- Monitoring or alerting

Testing is manual and local:

```bash
# Backend tests
cd backend
pytest

# Frontend (no test framework specified for v1)
```
