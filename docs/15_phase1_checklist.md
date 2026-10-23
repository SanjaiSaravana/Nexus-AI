# 15 — Phase 1 Implementation Checklist

## Overview

This is the actionable checklist for building Phase 1 of NEXUS AI. Phase 1 delivers:
**A functional, document-aware chatbot with authentication, document ingestion,
dense vector RAG, streaming responses, and basic observability.**

**Duration estimate**: ~10 weeks
**End-of-Phase Demo**: User uploads a resume, asks "What are my strongest skills?",
and receives an accurate, cited, streaming response.

---

## Setup & Infrastructure

### 1.1 Project Initialization
- [ ] Create GitHub repository `nexus-ai`
- [ ] Initialize monorepo directory structure (per `02_repository_structure.md`)
- [ ] Create `.gitignore` (Python, Node, .env, __pycache__, uploads/)
- [ ] Create `README.md` with setup instructions
- [ ] Create `CONTRIBUTING.md` with branch strategy and PR guidelines
- [ ] Create `.env.example` with all required variables (no values)

### 1.2 Docker Compose Setup
- [ ] Write `infra/docker/backend.Dockerfile` (Python 3.12-slim, non-root user)
- [ ] Write `infra/docker/frontend.Dockerfile` (Node 20 build + Nginx serve)
- [ ] Write `infra/docker/worker.Dockerfile` (same base as backend)
- [ ] Write `docker-compose.yml` with all services:
  - [ ] `postgres` (pgvector/pgvector:pg16)
  - [ ] `redis` (redis:7-alpine)
  - [ ] `neo4j` (neo4j:5-community) ← install but use in Phase 2
  - [ ] `backend`
  - [ ] `frontend`
  - [ ] `worker`
  - [ ] `langfuse`
  - [ ] `mlflow`
- [ ] Write `docker-compose.override.yml` for local dev (hot reload, port mapping)
- [ ] Write `scripts/setup_dev.sh` — one-command dev startup
- [ ] Test: `docker compose up` → all services healthy

### 1.3 CI Pipeline
- [ ] Create `.github/workflows/ci.yml`:
  - [ ] Backend: ruff, mypy, pytest unit + integration
  - [ ] Frontend: eslint, tsc, vitest
  - [ ] Security: pip-audit, npm audit
- [ ] Verify CI passes on first commit

---

## Backend — Core Setup

### 1.4 Python Project Configuration
- [ ] Create `backend/pyproject.toml` with:
  - [ ] All dependencies pinned to compatible versions
  - [ ] Dev dependencies (pytest, ruff, mypy, pytest-asyncio, httpx, factory-boy)
  - [ ] Ruff configuration (linting rules)
  - [ ] mypy configuration
  - [ ] pytest configuration (markers, asyncio_mode=auto)
- [ ] Create `backend/app/main.py` — FastAPI app factory with:
  - [ ] CORS middleware
  - [ ] Security headers middleware
  - [ ] Request ID middleware
  - [ ] Exception handlers
  - [ ] Router inclusion (`/api/v1/*`, `/api/health`)
- [ ] Create `backend/app/core/config.py` — Pydantic Settings:
  - [ ] Database settings
  - [ ] Redis settings
  - [ ] LLM provider settings
  - [ ] JWT settings
  - [ ] File storage settings

### 1.5 Database Setup
- [ ] Install pgvector extension SQL
- [ ] Create `backend/app/db/base.py` — SQLAlchemy async base
- [ ] Create `backend/app/db/session.py` — async session factory
- [ ] Create all SQLAlchemy models (per `03_database_design.md`):
  - [ ] `users`
  - [ ] `profiles`
  - [ ] `documents`
  - [ ] `document_chunks` (with `Vector(1536)` column)
  - [ ] `projects`
  - [ ] `tasks`
  - [ ] `goals`
  - [ ] `events`
  - [ ] `conversations`
  - [ ] `messages`
  - [ ] `memories`
  - [ ] `agent_runs`
  - [ ] `agent_steps`
  - [ ] `tool_calls`
  - [ ] `permissions`
  - [ ] `audit_logs`
  - [ ] `evaluations`
- [ ] Configure Alembic:
  - [ ] `alembic.ini`
  - [ ] `alembic/env.py` with async support
- [ ] Generate and apply initial migration
- [ ] Create all required indexes (including IVFFlat for vectors)
- [ ] Enable Row-Level Security on user-owned tables
- [ ] Test: All tables created, pgvector working

---

## Backend — Authentication

### 1.6 Auth Service
- [ ] Create `backend/app/core/security.py`:
  - [ ] `hash_password(password)` → bcrypt hash
  - [ ] `verify_password(plain, hashed)` → bool
  - [ ] `create_access_token(data)` → JWT
  - [ ] `create_refresh_token()` → opaque token
  - [ ] `verify_access_token(token)` → claims
- [ ] Create `backend/app/services/user_service.py`:
  - [ ] `create_user(email, password)`
  - [ ] `authenticate_user(email, password)`
  - [ ] `get_user_by_id(id)`
- [ ] Create `backend/app/core/dependencies.py`:
  - [ ] `get_current_user` FastAPI dependency
  - [ ] `get_db` session dependency

### 1.7 Auth API Routes
- [ ] Implement `POST /api/v1/auth/register`
- [ ] Implement `POST /api/v1/auth/login` → returns access + refresh token
- [ ] Implement `POST /api/v1/auth/refresh` → rotates refresh token
- [ ] Implement `POST /api/v1/auth/logout` → revokes refresh token in Redis
- [ ] Create `GET /api/health` and `GET /api/health/detailed`
- [ ] Unit tests for all auth functions
- [ ] Integration tests for all auth endpoints

---

## Backend — Document Ingestion

### 1.8 Document Parser
- [ ] Create `backend/app/ai/rag/chunker.py`:
  - [ ] `SemanticChunker.chunk(text, metadata)` → list of Chunks
  - [ ] Support heading-aware splitting for Markdown / DOCX
  - [ ] Sliding window fallback for plain text
  - [ ] Respect `MAX_CHUNK_SIZE = 512` tokens
  - [ ] Include overlap (`CHUNK_OVERLAP = 50` tokens)
- [ ] Create document parsers:
  - [ ] PDF parser (pdfplumber + PyMuPDF fallback)
  - [ ] DOCX parser (python-docx)
  - [ ] Plain text / Markdown parser
  - [ ] HTML parser (BeautifulSoup)
- [ ] Unit tests for chunker edge cases

### 1.9 Embedding Provider
- [ ] Create `backend/app/ai/embeddings/base.py` — abstract BaseEmbedder
- [ ] Create `backend/app/ai/embeddings/openai_embedder.py`:
  - [ ] `embed(texts: list[str])` → list of vectors
  - [ ] Batch processing (100 texts per call)
  - [ ] Retry with exponential backoff
- [ ] Create `backend/app/ai/embeddings/local_embedder.py` (sentence-transformers fallback)
- [ ] Create `EmbedderFactory` — returns provider from config
- [ ] Unit tests with mock OpenAI client

### 1.10 Document Service & Worker
- [ ] Create `backend/app/services/document_service.py`:
  - [ ] `create_document(user_id, file_data)` → saves file, creates DB record
  - [ ] `process_document(document_id)` → parse, chunk, embed, store
  - [ ] `delete_document(document_id)` → cascades to chunks
  - [ ] `get_document(document_id)`
  - [ ] `list_documents(user_id, page, per_page)`
- [ ] Create `backend/app/workers/document_processor.py` — Celery task
- [ ] Document API routes:
  - [ ] `POST /api/v1/documents/upload` (multipart)
  - [ ] `GET /api/v1/documents`
  - [ ] `GET /api/v1/documents/{id}`
  - [ ] `DELETE /api/v1/documents/{id}`
  - [ ] `GET /api/v1/documents/{id}/chunks`
- [ ] Integration tests for full ingestion pipeline

---

## Backend — RAG & Chat

### 1.11 LLM Provider
- [ ] Create `backend/app/ai/llm/base.py` — abstract BaseLLMProvider
- [ ] Create `backend/app/ai/llm/openai_provider.py`:
  - [ ] `chat(messages, tools, stream)` → response / async generator
  - [ ] Langfuse tracing on every call
  - [ ] Token counting
  - [ ] Cost estimation
- [ ] Create `LLMProviderFactory` — returns provider from config
- [ ] Unit tests with mock OpenAI client

### 1.12 RAG Retriever
- [ ] Create `backend/app/ai/rag/retriever.py`:
  - [ ] `dense_search(query_embedding, user_id, top_k)` → chunks (pgvector ANN)
  - [ ] (Phase 2) `sparse_search(query, user_id, top_k)` → placeholder
  - [ ] `retrieve(query, user_id, top_k=10)` → ranked chunks
- [ ] Create `backend/app/ai/rag/citation_builder.py`:
  - [ ] `build_citations(chunks)` → list of Citation objects
  - [ ] `inject_citations(response_text, citations)` → annotated text
- [ ] Unit tests for retrieval logic

### 1.13 Orchestrator & Chat
- [ ] Create `backend/app/ai/orchestrator/orchestrator.py`:
  - [ ] `process_message(user_id, message, conversation_id)` → async stream
  - [ ] Builds context: retrieve chunks + conversation history
  - [ ] Calls LLM with streaming
  - [ ] Stores message to DB
  - [ ] Records agent_run
- [ ] Chat API routes:
  - [ ] `POST /api/v1/chat/message` → SSE streaming response
  - [ ] `GET /api/v1/chat/conversations`
  - [ ] `GET /api/v1/chat/conversations/{id}`
  - [ ] `DELETE /api/v1/chat/conversations/{id}`
- [ ] Integration tests for chat flow (non-streaming)

---

## Backend — Observability

### 1.14 Langfuse Integration
- [ ] Add Langfuse client to `backend/app/core/config.py`
- [ ] Create `backend/app/ai/observability.py`:
  - [ ] `trace_llm_call(trace_id, input, output, model, tokens, cost)`
  - [ ] `trace_agent_run(agent_run_id, steps)`
- [ ] Instrument all LLM calls with Langfuse tracing
- [ ] Instrument all agent runs
- [ ] Test: Traces appear in Langfuse UI after sending a message

---

## Frontend — Phase 1

### 1.15 Frontend Setup
- [ ] Initialize Vite + React + TypeScript project in `frontend/`
- [ ] Install and configure Tailwind CSS
- [ ] Configure path aliases (`@/` → `src/`)
- [ ] Set up ESLint + Prettier
- [ ] Configure Vitest for unit tests
- [ ] Set up React Router for routing

### 1.16 Auth UI
- [ ] Create `LoginPage` — email/password form
- [ ] Create `RegisterPage` — registration form
- [ ] Create `authStore.ts` — JWT storage, auto-refresh
- [ ] Create `api/client.ts` — axios instance with auth headers + refresh interceptor
- [ ] Protected route wrapper component
- [ ] Test: Login, refresh, logout flow works

### 1.17 Document Upload UI
- [ ] Create `DocumentUploader` component — drag-and-drop file upload
- [ ] Create `DocumentList` component — list with status badges
- [ ] Create `Documents` page
- [ ] Integrate with document upload API
- [ ] Show processing status (pending → processing → complete → failed)

### 1.18 Chat UI
- [ ] Create `ChatWindow` component — message history display
- [ ] Create `MessageBubble` component — user and AI message styles
- [ ] Create `CitationCard` component — inline citation display
- [ ] Create `ChatInput` component — text input with send button
- [ ] Implement SSE streaming — stream tokens as they arrive
- [ ] Create `Chat` page
- [ ] Create `useChat` hook — manages conversation state
- [ ] Test: Send message, see streaming response with citations

### 1.19 Navigation & Layout
- [ ] Create app shell with sidebar navigation
- [ ] Responsive layout (mobile-first)
- [ ] Loading states for all async operations
- [ ] Error boundary with user-friendly error display
- [ ] Toast notifications for success/error feedback

---

## Testing & QA

### 1.20 Test Coverage
- [ ] Unit tests: `tests/unit/` → target > 80% coverage on new code
- [ ] Integration tests: `tests/integration/` → all API endpoints tested
- [ ] Test fixtures: sample PDF, DOCX, and plain text documents
- [ ] `conftest.py` with database fixtures and factory-boy factories
- [ ] CI passes all tests

### 1.21 Phase 1 Demo Validation
- [ ] Upload `sample_resume.pdf` as test user
- [ ] Wait for processing to complete (< 30 seconds for 2-page PDF)
- [ ] Ask: "What are my strongest programming skills?"
- [ ] Verify:
  - [ ] Response is accurate and relevant
  - [ ] Response streams token-by-token
  - [ ] At least one citation is present
  - [ ] Citation links to the correct document
  - [ ] Response stored in conversation history
  - [ ] Agent run recorded in `agent_runs` table
  - [ ] LLM call traced in Langfuse

---

## Documentation Updates

### 1.22 Developer Docs
- [ ] Update `README.md` with:
  - [ ] Prerequisites
  - [ ] One-command setup instructions
  - [ ] Running tests
  - [ ] Environment variable reference
- [ ] Generate and verify OpenAPI docs at `http://localhost:8000/docs`
- [ ] Add docstrings to all public functions

---

## Phase 1 Quality Gates

Before declaring Phase 1 complete:

| Gate | Criterion |
|------|-----------|
| ✅ All CI checks pass | ruff, mypy, pytest, eslint, tsc |
| ✅ Test coverage | > 80% on all new backend code |
| ✅ API documentation | All endpoints documented in OpenAPI |
| ✅ Performance | RAG query < 3s P95 on local machine |
| ✅ Demo works | Upload → query → cited answer in < 60s end-to-end |
| ✅ Observability | All LLM calls visible in Langfuse |
| ✅ Security | No secrets in code, RLS enabled, JWT working |
| ✅ Docker | `docker compose up` → everything starts in < 2 minutes |
