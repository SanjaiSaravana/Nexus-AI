# Deployment Architecture & Operations Guide

> **NEXUS AI — Production Docker Compose, Local Setup & Infrastructure**

This document details the deployment architecture of NEXUS AI, covering container topology, Docker Compose configuration, local development setup, environment variables, health checks, database migrations, and operational resilience.

---

## 1. Service Topology

NEXUS AI deploys as a multi-container stack orchestrated via Docker Compose:

```mermaid
flowchart TD
    subgraph Client["Public Network / Browser"]
        Browser["User Browser (Port 3000)"]
    end

    subgraph DockerCompose["Docker Compose Network (nexus-network)"]
        Frontend["frontend container\n(React 19 + Nginx :80 -> :3000)"]
        Backend["backend container\n(FastAPI + Uvicorn :8000 -> :8000)"]
        Postgres["postgres container\n(pgvector/pgvector:pg16 :5432)"]
        Neo4j["neo4j container\n(neo4j:5.20-community :7474, :7687)"]
        
        Frontend -->|API Requests / Proxy| Backend
        Backend -->|Async SQLAlchemy / pgvector| Postgres
        Backend -->|Bolt Protocol 7687| Neo4j
    end

    Browser --> Frontend
    Browser -.->|Direct API Docs| Backend
```

---

## 2. Docker Compose Configuration

The root `docker-compose.yml` configures all four core services:

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: nexus-postgres
    restart: always
    environment:
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: nexuspassword
      POSTGRES_DB: nexus_ai
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexus -d nexus_ai"]
      interval: 5s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5.20-community
    container_name: nexus-neo4j
    restart: always
    environment:
      NEO4J_AUTH: neo4j/nexuspassword
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p nexuspassword 'RETURN 1'"]
      interval: 10s
      timeout: 10s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nexus-backend
    restart: always
    environment:
      DATABASE_URL: postgresql+asyncpg://nexus:nexuspassword@postgres:5432/nexus_ai
      SECRET_KEY: nexus-super-secret-key-for-jwt-token-signing-32b
      PROJECT_NAME: "NEXUS AI"
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: nexuspassword
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: nexus-frontend
    restart: always
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  neo4j_data:
```

### Launching the Stack
```bash
docker compose up --build
```

### Service Access URLs
- **Web Application**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
- **Neo4j Browser Console**: [http://localhost:7474](http://localhost:7474)

---

## 3. Local Development Setup (Without Docker)

For rapid local testing and offline development:

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (uses SQLite fallback by default)
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server with hot module replacement (HMR)
npm run dev
```
Frontend runs at [http://localhost:5173](http://localhost:5173) and proxies API calls to [http://localhost:8000](http://localhost:8000).

---

## 4. Environment Variables Reference

All settings are validated via Pydantic `BaseSettings` (`app.core.config.Settings`):

| Variable | Default Value | Description |
|---|---|---|
| `PROJECT_NAME` | `"NEXUS AI"` | Application title |
| `SECRET_KEY` | *Required in prod* | Secret key for HS256 JWT signature verification |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | JWT token lifespan |
| `DATABASE_URL` | `sqlite+aiosqlite:///./nexus.db` | Async database connection string |
| `OPENAI_API_KEY` | `""` (Optional) | OpenAI API key for remote LLM & embeddings (works offline if omitted) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API endpoint URL |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j database user |
| `NEO4J_PASSWORD` | `nexuspassword` | Neo4j database password |
| `NEO4J_DATABASE` | `neo4j` | Neo4j active database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache connection string |
| `EMBEDDING_DIM` | `384` | Vector embedding dimensionality |
| `MAX_UPLOAD_SIZE_MB` | `25` | Maximum upload size ceiling |

---

## 5. Automated Database Migrations (Alembic)

Database schema evolution is managed via Alembic:

```bash
cd backend

# Check current migration revision
alembic current

# Apply all pending migrations to head
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "add_new_feature_table"

# Rollback one migration step
alembic downgrade -1
```

---

## 6. Operational Resilience & Fallback Architecture

NEXUS AI is engineered to avoid hard failures if downstream infrastructure components are offline:

1. **Database Fallback**: When PostgreSQL is unavailable, switching `DATABASE_URL` to `sqlite+aiosqlite:///./nexus.db` runs full async CRUD with JSON-serialized vectors.
2. **Graph Fallback**: If the Neo4j container drops or is offline, `InMemoryGraphStore` automatically assumes responsibility for entity and relationship queries with zero application downtime.
3. **Cache Fallback**: If Redis drops connection, `InMemoryCacheStore` provides local in-memory key-value caching with TTL expiration.
4. **AI Fallback**: If remote LLM API keys are unset, local deterministic heuristics handle RAG synthesis, topic decomposition, and task generation.

---

## 7. Production Hardening Checklist

When deploying NEXUS AI to production environments:
- [x] Configure SSL/TLS termination using Nginx or an Application Load Balancer.
- [x] Rotate `SECRET_KEY` with a cryptographically secure 64-character random string.
- [x] Enforce PostgreSQL database backups using automated `pg_dump` snapshots.
- [x] Mount persistent Docker volumes for `postgres_data` and `neo4j_data`.
- [x] Verify that `.env` is excluded from git repositories (`.gitignore`).
- [x] Confirm rate limiting middleware is active (`15 req/min` on auth, `300 req/min` general).
