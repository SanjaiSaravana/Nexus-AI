# NEXUS AI
> **Agentic Personal Intelligence & Productivity Platform**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](backend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](backend/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](frontend/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](frontend/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-4169E1?logo=postgresql&logoColor=white)](docker-compose.yml)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.20_Graph-008CC1?logo=neo4j&logoColor=white)](docker-compose.yml)
[![Tests](https://img.shields.io/badge/Tests-121%20Passed-brightgreen)](backend/tests/)

NEXUS AI is an autonomous, privacy-first personal intelligence and productivity platform. It synthesizes conversational AI, multi-format document intelligence, zero-hallucination hybrid RAG, an adaptive 4-tier cognitive memory system, and an entity-relationship knowledge graph into a unified multi-agent orchestrator with human-in-the-loop tool safety.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [AI Architecture](#ai-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database](#database)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Docker](#docker)
- [Testing](#testing)
- [AI Evaluation](#ai-evaluation)
- [Security](#security)
- [Screenshots](#screenshots)
- [Demo](#demo)
- [Future Improvements](#future-improvements)
- [Limitations](#limitations)
- [License](#license)

---

## Problem Statement

Modern knowledge workers and professionals suffer from **severe personal information fragmentation**:
1. **Scattered Silos**: Vital context is spread across disparate resumes, job descriptions, PDFs, markdown notes, calendar schedules, task trackers, and email threads.
2. **Stateless AI Chatbots**: Standard LLMs forget previous conversations, require repetitive prompt context, and lack long-term recall of user strengths, preferences, or career goals.
3. **Uncontrolled Tool Execution**: Fragile autonomous agents often hallucinate external API calls, modify schedules, or delete tasks without user authorization or auditable controls.
4. **Passive Interfaces**: Traditional productivity apps require manual input for everything, while passive AI assistants wait to be prompted rather than proactively detecting risks, upcoming interview prep gaps, or overlapping commitments.

---

## Solution

**NEXUS AI** introduces a **unified personal intelligence layer** that bridges structured productivity data with unstructured cognitive intelligence:
- **Unified Knowledge Mesh**: Links relational records (projects, tasks, goals), vector embeddings (documents, chunks), and a Neo4j knowledge graph into a cohesive graph of personal context.
- **Continuous 4-Tier Cognitive Memory**: Automatically classifies and updates Semantic facts, Episodic experiences, Procedural preferences, and Working session state while filtering out conversational noise.
- **Hierarchical Multi-Agent Orchestrator**: Decomposes high-level natural language goals into ordered subtasks delegated to specialized agents (Planner, Research, Memory, Project, Task, Calendar, and Execution).
- **Zero-Trust Security & Human-in-the-Loop Tool Safety**: Strict tenant data isolation, prompt-injection defense delimiters, and a 5-step security guard requiring explicit human confirmation before executing any high-risk external action.
- **Autonomous Proactive Detection**: Silently evaluates temporal deadlines, interview schedules, and inactive goals to generate timely, high-value recommendations with anti-spam caps.

---

## Key Features

- **AI Chat**: Real-time token streaming via Server-Sent Events (SSE) with dynamic activity updates (`Planning...`, `Retrieving documents...`), conversation history, and clickable source citations.
- **RAG (Retrieval-Augmented Generation)**: Dual-channel hybrid retrieval combining dense vector similarity with BM25 sparse keyword matching, fused via Reciprocal Rank Fusion (RRF $k=60$) with an anti-hallucination guard.
- **Document Intelligence**: Multi-format parsing for PDF, DOCX, TXT, Markdown, and CSV with magic bytes header inspection, sliding-window chunking (~500 tokens, 100 token overlap), and entity extraction.
- **Personal Memory**: 4-tier cognitive memory architecture (Semantic, Episodic, Procedural, Working) with conversational noise filtering, 3rd-person canonicalization, importance scoring, and semantic deduplication.
- **Knowledge Graph**: Neo4j graph database modeling 11 node entities (`User`, `Project`, `Skill`, `Technology`, `Document`, `Task`, `Goal`, `Event`, `Company`, `Job`, `Topic`) and 10 typed directed relationships with an interactive canvas force-directed viewer.
- **Multi-Agent AI**: Specialized agents (Planner, Research, Memory, Project, Task, Calendar, Execution) managed by a central orchestrator with state isolation, retry backoffs, and safe activity streaming.
- **Task Planning**: Intelligent decomposition of complex user requests into prioritized, category-tagged tasks with automatic database persistence.
- **Recommendations**: Proactive recommendation feed with priority scoring, related deadlines, single-click action execution, and category dismissal memory.
- **Calendar Intelligence**: Bi-directional calendar orchestration, free-slot discovery algorithms, conflict detection, and event scheduling.
- **Controlled Tool Execution**: 9 registered tool domains (`task`, `calendar`, `documents`, `memory`, `projects`, `knowledge_graph`, `search`, `email`, `github`) governed by a 5-step security guard requiring user confirmation for sensitive actions.
- **Proactive Intelligence**: Autonomous detection of 8 operational situations (e.g., preparation gaps for tomorrow's interview, overlapping events, inactive goals) with a 6-factor priority engine.
- **AI Evaluation**: Quantitative evaluation suite measuring Context Precision, Context Recall, Answer Relevance, Faithfulness, Citation Accuracy, Task Success Rate, and Planning Accuracy.
- **Observability**: End-to-end distributed waterfall tracing across 7 pipeline stages, latency percentiles (p50, p95, p99), token counters, and cost estimation.
- **Security**: STRIDE-hardened zero-trust architecture, structural prompt boundary delimiters (`<SYSTEM>`, `<RETRIEVED_DOCUMENT>`, `<TOOL_OUTPUT>`), bcrypt password hashing, HS256 JWT auth, and credential redaction.

---

## Architecture

The following diagram illustrates the complete end-to-end architecture of NEXUS AI:

```mermaid
flowchart TD
    subgraph ClientTier["Frontend Tier (React 19 + TypeScript + Vite)"]
        UI_Chat["Chat Interface (SSE Stream)"]
        UI_Dash["Executive Dashboard"]
        UI_KG["Knowledge Graph Canvas"]
        UI_Mem["Memory Manager"]
        UI_Eval["AI Evaluation & Observability"]
        UI_Actions["Action Confirmation Modal"]
    end

    subgraph GatewayTier["API Gateway & Security Layer (FastAPI)"]
        MW_Sec["Security Headers & CORS"]
        MW_Rate["Sliding Window Rate Limiter"]
        MW_Auth["OAuth2 / JWT Authentication"]
        MW_Err["Sanitized Error Masking"]
    end

    subgraph MultiAgentTier["Multi-Agent Orchestration Tier"]
        Orchestrator["Agent Orchestrator"]
        Planner["Planner Agent"]
        Research["Research Agent"]
        MemAgent["Memory Agent"]
        ProjAgent["Project Agent"]
        TaskAgent["Task Agent"]
        CalAgent["Calendar Agent"]
        ExecAgent["Execution Agent"]
    end

    subgraph IntelligenceTier["Intelligence & Cognitive Subsystems"]
        RAG["Hybrid RAG (Dense + BM25 Sparse + RRF)"]
        MemoryEngine["4-Tier Cognitive Memory Engine"]
        KGEngine["Neo4j Knowledge Graph Engine"]
        ProactiveEngine["Proactive Situation Detector"]
        PromptGuard["Prompt Guard & Delimiter Isolation"]
    end

    subgraph SafetyTier["Security & Action Layer"]
        SecurityGuard["5-Step Tool Security Guard"]
        ActionManager["Action Proposal & HITL Approval"]
        AuditLog["Credential-Sanitized Audit Trail"]
    end

    subgraph StorageTier["Persistence & Infrastructure Layer"]
        PG[("PostgreSQL 16 + pgvector")]
        Neo4jDB[("Neo4j 5.20 Community")]
        RedisCache[("Redis Cache / In-Memory Fallback")]
        MLflowStore[("MLflow Experiment Tracking")]
    end

    subgraph ToolTier["Tool Integrations (9 Domains)"]
        Tools["Calendar, Task, Docs, Memory, Projects, KG, Search, Email, GitHub"]
    end

    ClientTier <-->|REST API / SSE Streams| GatewayTier
    GatewayTier --> Orchestrator
    
    Orchestrator --> Planner
    Planner --> Research & MemAgent & ProjAgent & TaskAgent & CalAgent & ExecAgent
    
    Research --> PromptGuard --> RAG
    MemAgent --> MemoryEngine
    ProjAgent --> KGEngine & PG
    TaskAgent --> PG
    CalAgent --> Tools
    ExecAgent --> SecurityGuard
    
    SecurityGuard --> ActionManager
    ActionManager -->|Pending Proposal| UI_Actions
    UI_Actions -->|Approved / Rejected| ActionManager
    ActionManager --> Tools
    ActionManager --> AuditLog --> PG
    
    RAG --> PG
    MemoryEngine --> PG
    KGEngine --> Neo4jDB
    ProactiveEngine --> PG & UI_Dash
    Orchestrator -.-> MLflowStore
```

---

## How It Works

NEXUS AI coordinates multiple intelligence subsystems to transform open-ended user requests into concrete, verified actions.

### The Flagship Workflow: Autonomous Interview Preparation

Consider the user prompt:
> **"I have an interview tomorrow. Help me prepare."**

The platform executes a 16-step end-to-end autonomous pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant ChatUI as Web App (Chat UI)
    participant Orch as Agent Orchestrator
    participant Planner as Planner Agent
    participant Vault as Knowledge Vault (RAG)
    participant Graph as Neo4j Knowledge Graph
    participant Memory as Memory Engine
    participant Security as Security Guard (HITL)
    participant DB as Relational Database

    User->>ChatUI: "I have an interview tomorrow. Help me prepare."
    ChatUI->>Orch: POST /api/v1/workflows/interview-prep
    Orch-->>ChatUI: SSE: "Understanding request..."
    Orch->>Planner: Decompose Goal into 8 Subtasks
    
    Orch-->>ChatUI: SSE: "Finding interview..."
    Orch->>DB: Query CalendarEvent for tomorrow's interview
    DB-->>Orch: Event: "Senior Cloud Engineer at Stripe"
    
    Orch-->>ChatUI: SSE: "Reading job description..."
    Orch->>Vault: Hybrid RAG Search for Stripe Job Description
    Vault-->>Orch: Required: AWS, Kubernetes, Distributed Systems, SQL
    
    Orch-->>ChatUI: SSE: "Analyzing your skills..."
    Orch->>Graph: Query User Skills & Project Connections
    Orch->>Memory: Retrieve Relevant Episodic & Semantic Memories
    Graph-->>Orch: Verified Skills: Python, Docker, Fast-API
    Memory-->>Orch: Memory: Built microservices, loves STAR stories
    
    Orch-->>ChatUI: SSE: "Identifying skill gaps..."
    Orch->>Orch: Build Competency Matrix (Strong vs. Weak vs. Missing)
    
    Orch-->>ChatUI: SSE: "Creating preparation plan..."
    Orch->>DB: Persist 4 Actionable Tasks (SQL, System Design, Projects, Mock)
    
    Orch-->>ChatUI: SSE: "Waiting for calendar approval..."
    Orch->>Security: Stage Calendar ActionProposal (6:00 PM – 9:30 PM Blocks)
    Security-->>ChatUI: Render Action Confirmation Card [Approve] [Reject]
    
    User->>ChatUI: Click [Approve]
    ChatUI->>Security: POST /api/v1/actions/proposals/{id}/approve
    Security->>DB: Insert Calendar Events & Write Sanitized Audit Log
    
    Orch->>Memory: Store Episodic Memory: "Prepared for Stripe Cloud Interview"
    Orch-->>ChatUI: SSE: "Completed."
    Orch-->>ChatUI: Render Executive Readiness Briefing + Study Plan
```

1. **Detect & Locate**: Identifies user intent (`Interview Preparation`), extracts the deadline (`Tomorrow`), and finds the scheduled interview event on the calendar.
2. **Context Ingestion**: Retrieves the matching job description from the Knowledge Vault and extracts key requirements, responsibilities, and competencies.
3. **Skill & Project Analysis**: Retrieves candidate resume details, database projects, and episodic memories, cross-referencing user competencies against job requirements.
4. **Gap Analysis**: Identifies strong competencies, weak areas, and missing concepts, synthesizing tailored technical topics and STAR narratives.
5. **Action Generation**: Converts the study plan into 4 persistent database tasks with assigned priorities and categories.
6. **Human-in-the-Loop Scheduling**: Discovers open slots on the calendar and stages an `ActionProposal`. The system halts and requests user confirmation before inserting events.
7. **Memory Reinforcement**: Automatically stores an episodic memory recording the preparation session and synthesized interview goals.
8. **Executive Briefing**: Delivers a structured markdown summary with study time blocks, practice questions, and clickable citations.

---

## AI Architecture

NEXUS AI's intelligence tier is structured into modular, provider-agnostic, and fully decoupled components:

| Component | Architecture & Implementation | Key Mechanism |
|---|---|---|
| **LLM Engine** | Provider-agnostic abstraction (`OpenAI`, `Anthropic`, `Gemini`, `Ollama`) with local heuristic fallback | Configurable via `.env`; supports streaming responses via Server-Sent Events (SSE). |
| **Hybrid RAG** | Dual-channel dense vector + BM25 sparse lexical search | Reciprocal Rank Fusion (RRF $k=60$) with $w_{\text{dense}}=0.7$, $w_{\text{sparse}}=0.3$; anti-hallucination guard (`RELEVANCE_THRESHOLD=0.08`). |
| **Embeddings** | Pluggable `EmbeddingService` | Supports OpenAI `text-embedding-3-small` and a built-in deterministic 384-dimensional dense vectorizer for zero-cost, offline execution. |
| **Cognitive Memory** | 4-tier memory architecture (Semantic, Episodic, Procedural, Working) | Conversational noise filter, 3rd-person canonicalization, importance scoring ($\ge 0.40$), and cosine deduplication ($0.82$). |
| **Knowledge Graph** | Neo4j 5.20 Community with APOC + in-memory store fallback | 11 typed node labels, 10 directed relationships, automated document entity extraction, and relational database synchronization. |
| **Multi-Agent System**| Central `AgentOrchestrator` managing 7 specialized agents | Isolated execution state tracking (`run_id`, `status`, `retries`), exponential backoff, and privacy-preserving UI activity streaming (no chain-of-thought leaks). |
| **Tools & Safety** | 9 registered tool domains + 5-step `ToolSecurityGuard` | Enforces permissions, sanitizes inputs, assesses risk (`read_only` to `critical`), and mandates human approval for external actions. |

---

## Tech Stack

| Layer | Technologies | Version / Notes |
|---|---|---|
| **Frontend UI** | React, TypeScript, Vite, Lucide Icons | React 19, Vite 8, pure modern custom CSS design system |
| **Backend Framework**| FastAPI, Uvicorn, Pydantic v2 | Python 3.11+, Async ASGI, strict schema validation |
| **Database & ORM** | PostgreSQL 16, pgvector, SQLAlchemy 2.0, Alembic | Async SQLAlchemy (`asyncpg`), `vector(384)`, SQLite + `aiosqlite` fallback |
| **Graph Database** | Neo4j Community, Cypher Query Language | Neo4j 5.20 with APOC plugin, resilient in-memory graph fallback |
| **Cache & Key-Value** | Redis 7, In-Memory Cache Store | Async Redis client with transparent in-memory TTL fallback |
| **Document Parsing** | `pypdf`, `python-docx`, native CSV/Markdown parsers | Magic bytes header validation, sliding window chunker |
| **Security & Auth** | Passlib, Bcrypt, Python-Jose (JWT) | HS256 signed JWTs, bcrypt password hashing, delimiter isolation |
| **MLOps & Evaluation**| MLflow, Custom Benchmark Suite | MLflow 3.17.1 tracking, RAG & Agent evaluation suites |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX | 121 automated async unit and integration tests |
| **DevOps & Containers**| Docker, Docker Compose, Nginx | Multi-stage Dockerfiles, health checks, automated migrations |

---

## Project Structure

```text
Nexus-AI/
├── docker-compose.yml              # Complete 4-service stack (Postgres+pgvector, Neo4j, Backend, Frontend)
├── LICENSE                         # MIT Open-Source License
├── README.md                       # Platform documentation and portfolio presentation
├── backend/
│   ├── Dockerfile                  # Production multi-stage backend container
│   ├── alembic.ini                 # Database migration configuration
│   ├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, pgvector, Neo4j, MLflow)
│   ├── .env.example                # Documented configuration template
│   ├── alembic/                    # Database migration versions
│   │   ├── env.py
│   │   └── versions/               # Automated schema migrations
│   ├── app/
│   │   ├── main.py                 # FastAPI application entrypoint, middleware, and route mounting
│   │   ├── api/
│   │   │   ├── deps.py             # FastAPI dependencies (auth, database session, permissions)
│   │   │   └── v1/                 # 18 Versioned REST API routers
│   │   │       ├── actions.py      # Tool execution & human confirmation endpoints
│   │   │       ├── agents.py       # Multi-agent orchestrator inspection
│   │   │       ├── auth.py         # User registration & JWT login
│   │   │       ├── calendar.py     # Calendar event CRUD & free slot discovery
│   │   │       ├── chat.py         # Streaming RAG chat with tool calling & citations
│   │   │       ├── dashboard.py    # Executive metrics & aggregate overview
│   │   │       ├── documents.py    # Document upload, parsing, and chunk management
│   │   │       ├── evaluation.py   # RAG & Multi-Agent evaluation suite endpoints
│   │   │       ├── goals.py        # Strategic goal tracking
│   │   │       ├── knowledge_graph.py # Graph query, node inspection, and sync
│   │   │       ├── memories.py     # 4-tier memory CRUD and search
│   │   │       ├── mlops.py        # MLflow experiment and registry status
│   │   │       ├── observability.py# Waterfall distributed traces and system metrics
│   │   │       ├── projects.py     # Project CRUD operations
│   │   │       ├── recommendations.py # Proactive intelligence recommendations
│   │   │       ├── tasks.py        # Task CRUD and prioritization
│   │   │       ├── users.py        # User profile management
│   │   │       └── workflows.py    # Flagship interview preparation workflow
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic BaseSettings environment configuration
│   │   │   ├── database.py         # Async SQLAlchemy engine and session factory
│   │   │   ├── middleware.py       # Security headers, rate limiting, and exception masking
│   │   │   ├── prompt_guard.py     # Delimiter boundaries and prompt injection defense
│   │   │   ├── redis_client.py     # Resilient Redis cache with in-memory fallback
│   │   │   └── security.py         # Bcrypt password hashing and JWT token handling
│   │   ├── evaluation/             # AI evaluation suites and benchmark datasets
│   │   │   ├── agent_evaluator.py  # Task success, planning accuracy, tool selection F1
│   │   │   ├── datasets.py         # Golden benchmark evaluation test cases
│   │   │   ├── rag_evaluator.py    # Precision, recall, faithfulness, citation accuracy
│   │   │   └── runner.py           # Automated evaluation runner
│   │   ├── mlops/
│   │   │   └── mlflow_service.py   # MLflow tracking and versioned asset registry
│   │   ├── models/                 # SQLAlchemy ORM declarative models
│   │   │   ├── action.py           # Action proposals and immutable audit logs
│   │   │   ├── calendar.py         # Calendar events
│   │   │   ├── chat.py             # Chat sessions and messages
│   │   │   ├── document.py         # Documents and vector chunks
│   │   │   ├── goal.py             # Strategic goals
│   │   │   ├── memory.py           # 4-tier cognitive memories
│   │   │   ├── project.py          # User projects
│   │   │   ├── recommendation.py   # Proactive recommendations
│   │   │   ├── task.py             # Tasks and milestones
│   │   │   └── user.py             # User accounts and profiles
│   │   ├── observability/
│   │   │   ├── metrics.py          # Latency percentiles, tokens, costs, and error rates
│   │   │   └── tracer.py           # 7-stage distributed waterfall span tracer
│   │   ├── schemas/                # Pydantic v2 validation and serialization schemas
│   │   └── services/               # Core business and AI service layers
│   │       ├── document_pipeline.py# Validation, parsing, and chunking pipeline
│   │       ├── embedding.py        # OpenAI and local dense vectorizer
│   │       ├── memory_service.py   # Noise filtering, extraction, deduplication, retrieval
│   │       ├── rag_service.py      # Hybrid retrieval, RRF reranking, citation assembly
│   │       ├── agents/             # Multi-agent implementations (Planner, Research, etc.)
│   │       ├── graph/              # Neo4j client, extractor, and in-memory graph store
│   │       ├── proactive/          # Proactive detector and 6-factor priority engine
│   │       ├── tools/              # 9 Tool domains, registry, action manager, security guard
│   │       └── workflows/          # 16-step flagship interview preparation workflow
│   └── tests/                      # Comprehensive automated test suite (121 tests)
├── docs/                           # In-depth architectural specifications
│   ├── architecture.md             # System architecture and full-stack topology
│   ├── ai-architecture.md          # AI subsystems, LLM abstraction, and multi-agent design
│   ├── rag.md                      # Hybrid retrieval, RRF reranking, and chunking pipeline
│   ├── memory.md                   # 4-tier cognitive memory architecture and algorithms
│   ├── knowledge-graph.md          # Neo4j graph ontology, Cypher querying, and UI canvas
│   ├── agents.md                   # Multi-agent orchestrator, agent roles, and activity streams
│   ├── tools.md                    # 9 tool domains, 5-step security guard, and HITL actions
│   ├── security.md                 # Threat model, prompt injection defense, and IDOR mitigation
│   ├── evaluation.md               # RAG benchmark metrics, agent evaluations, and MLOps
│   └── deployment.md               # Production Docker Compose, local setup, and operations
└── frontend/
    ├── Dockerfile                  # Production Nginx frontend container
    ├── package.json                # React 19, TypeScript, Lucide Icons, Vite
    ├── vite.config.ts              # Vite configuration and backend API proxying
    └── src/
        ├── App.tsx                 # Client routing, global layout, and navigation
        ├── index.css               # Modern AI SaaS design system (pure CSS)
        ├── components/             # Reusable UI components (Sidebar, Navbar, Modals)
        ├── context/                # AuthContext and state management
        ├── pages/                  # 12 Web application views
        │   ├── Actions.tsx         # Action approval cards and immutable audit log viewer
        │   ├── Chat.tsx            # Streaming chat with citations and tool activity
        │   ├── Dashboard.tsx       # Executive overview, productivity metrics, recommendations
        │   ├── Evaluation.tsx      # RAG metrics, agent gauges, waterfall trace visualizer
        │   ├── Goals.tsx           # Strategic goals and milestone progress bars
        │   ├── KnowledgeGraph.tsx  # Force-directed HTML5 canvas graph explorer
        │   ├── Login.tsx           # Secure user authentication
        │   ├── Memory.tsx          # Cognitive memory manager with type filters and CRUD
        │   ├── Projects.tsx        # Projects CRUD with task counts
        │   ├── Register.tsx        # User registration
        │   ├── Settings.tsx        # Proactive frequency, volume caps, and API settings
        │   └── Tasks.tsx           # Prioritized task board with status filters
        ├── services/               # API client connectors (fetch with auth interceptors)
        └── types/                  # TypeScript interfaces matching backend Pydantic models
```

---

## Database

NEXUS AI utilizes a polyglot persistence architecture combining relational, vector, and graph databases with strict multi-tenant isolation:

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : "owns"
    USERS ||--o{ TASKS : "owns"
    USERS ||--o{ GOALS : "owns"
    USERS ||--o{ DOCUMENTS : "owns"
    USERS ||--o{ MEMORIES : "owns"
    USERS ||--o{ CALENDAR_EVENTS : "owns"
    USERS ||--o{ ACTION_PROPOSALS : "owns"
    USERS ||--o{ AUDIT_LOGS : "owns"
    USERS ||--o{ RECOMMENDATIONS : "owns"
    
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "contains"
    PROJECTS ||--o{ TASKS : "contains"
    
    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        timestamp created_at
    }
    
    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        string filename
        string file_type
        int file_size
        string checksum_sha256
    }
    
    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid user_id FK
        int chunk_index
        text content
        vector_384 embedding
    }
    
    MEMORIES {
        uuid id PK
        uuid user_id FK
        string memory_type
        text content
        float importance
        int access_count
        vector_384 embedding
    }
    
    ACTION_PROPOSALS {
        uuid id PK
        uuid user_id FK
        string tool_name
        string action_name
        string risk_level
        string status
        json parameters
    }
```

### Relational & Vector Schema (PostgreSQL 16 + pgvector)
- **Multi-Tenant User Isolation**: Every primary table includes a non-nullable `user_id` foreign key referencing `users.id`. All database queries strictly enforce `WHERE user_id = current_user.id`.
- **pgvector Integration**: `document_chunks.embedding` and `memories.embedding` store 384-dimensional dense vectors indexed with cosine distance (`<=>`).
- **SQLite Fallback**: For lightweight local testing or offline development without Docker, NEXUS automatically falls back to SQLite via `aiosqlite` with JSON-serialized vector similarity computation.

### Knowledge Graph Schema (Neo4j 5.20 Community)
- **Node Labels**: `User`, `Project`, `Skill`, `Technology`, `Document`, `Task`, `Goal`, `Event`, `Company`, `Job`, `Topic`.
- **Relationship Types**: `OWNS`, `USES`, `KNOWS`, `REQUIRES`, `DESCRIBES`, `SUPPORTS`, `RELATES_TO`, `HAS_TASK`, `HAS_GOAL`, `WORKS_AT`.
- **Tenant Scope**: All Neo4j nodes include an indexed `user_id` property. Queries are parameterized (`MATCH (n {user_id: $user_id})`) to guarantee multi-tenant partitioning.
- **In-Memory Store Fallback**: If Neo4j is offline or unavailable, `InMemoryGraphStore` seamlessly provides graph persistence and Cypher-like traversals.

---

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git
- Docker and Docker Compose (recommended)

### 1. Clone the Repository
```bash
git clone https://github.com/SanjaiSaravana/Nexus-AI.git
cd Nexus-AI
```

### 2. Backend Local Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your local environment configuration
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the FastAPI development server
uvicorn app.main:app --reload --port 8000
```
The backend API is now running at [http://localhost:8000](http://localhost:8000). Interactive Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. Frontend Local Setup
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
The frontend web application is now running at [http://localhost:5173](http://localhost:5173).

---

## Environment Variables

Configuration is managed via Pydantic `BaseSettings`. Create a `.env` file in the `backend/` directory based on `.env.example`:

```bash
# ==============================================================================
# NEXUS AI Configuration Template
# ==============================================================================

# Application Settings
PROJECT_NAME="NEXUS AI"
SECRET_KEY="replace-with-a-secure-random-secret-key-min-32-chars-long"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Configuration
# Local SQLite fallback:
DATABASE_URL="sqlite+aiosqlite:///./nexus.db"
# Production PostgreSQL + pgvector:
# DATABASE_URL="postgresql+asyncpg://nexus:nexuspassword@localhost:5432/nexus_ai"

# Optional External LLM & Embeddings
# (Nexus AI runs 100% offline with zero cost if omitted, using local dense embeddings & heuristics)
# OPENAI_API_KEY="sk-..."
# OPENAI_BASE_URL="https://api.openai.com/v1"

# Neo4j Knowledge Graph Configuration
# (Automatically falls back to built-in in-memory graph repository if offline)
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="nexuspassword"
NEO4J_DATABASE="neo4j"

# Redis Cache Configuration
# (Automatically falls back to in-memory TTL cache if offline)
REDIS_URL="redis://localhost:6379/0"

# CORS Configuration
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]
```

> **Security Note:** Never commit `.env` or real API keys to version control. The repository includes `.gitignore` rules preventing `.env` leaks.

---

## Docker

Run the entire NEXUS AI ecosystem (PostgreSQL with `pgvector`, Neo4j Community, FastAPI Backend, and Nginx Frontend) with a single command:

```bash
docker compose up --build
```

### Docker Service Topology
- **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend & API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Neo4j Browser Console**: [http://localhost:7474](http://localhost:7474) (bolt on `7687`)
- **PostgreSQL Database**: Port `5432`

To stop all services and persist database volumes:
```bash
docker compose down
```

---

## Testing

NEXUS AI includes a comprehensive automated test suite covering all 9 platform phases:

```bash
# Navigate to backend
cd backend

# Run the complete test suite
pytest -v

# Run tests with short progress summary
pytest -q
```

### Test Coverage Highlights (121 Tests Passed)
- `test_auth.py`: User registration, login, password complexity, and JWT issuance.
- `test_isolation.py`: Cross-tenant IDOR attack defenses and user-scoping assertions.
- `test_rag.py` & `test_rag_eval.py`: Ingestion, sliding-window chunking, dense+sparse hybrid retrieval, RRF reranking, citation mapping, and anti-hallucination guard.
- `test_memory.py`: Conversational noise filtering, 4-tier classification, importance scoring, and semantic deduplication.
- `test_knowledge_graph.py`: Entity and relationship ingestion, Cypher querying, and in-memory store fallback.
- `test_multi_agent.py`: Planner decomposition, multi-agent orchestrator execution, and state tracking.
- `test_tools_and_actions.py`: 5-step security guard, tool schemas, and human confirmation approval lifecycle.
- `test_flagship_workflow.py`: End-to-end 16-step interview preparation workflow with HITL calendar approval.
- `test_proactive_intelligence.py`: Autonomous detection across 8 situations and 6-factor priority scoring.
- `test_evaluation_observability_mlops.py`: RAG evaluator, agent evaluator, 7-stage waterfall tracer, and MLflow registry.
- `test_security_hardening.py`: PromptGuard boundary delimiter defense and malicious file upload rejection.
- `test_failure_scenarios.py`: Resilient degradation during Neo4j, Redis, or external service outages.
- `test_production_integration.py`: End-to-end production request lifecycle verification.

---

## AI Evaluation

NEXUS AI includes built-in quantitative evaluation engines benchmarking both retrieval accuracy and multi-agent operations:

### 1. RAG Benchmark Metrics
Evaluated against golden benchmark ground-truth datasets:

| Metric | Target | Formula / Logic | Description |
|---|---|---|---|
| **Context Precision** | $\ge 90\%$ | $\frac{\text{Relevant Retrieved Chunks}}{\text{Total Retrieved Chunks}}$ | Measures signal-to-noise ratio in retrieved context; penalizes irrelevant chunks. |
| **Context Recall** | $\ge 90\%$ | $\frac{\text{Ground Truth Items Retrieved}}{\text{Total Ground Truth Items}}$ | Evaluates whether retrieval captured all necessary ground-truth facts. |
| **Answer Relevance** | $\ge 95\%$ | Semantic alignment & fact coverage | Measures how directly the response addresses the prompt. |
| **Faithfulness** | $\ge 95\%$ | $\frac{\text{Grounded Claims}}{\text{Total Claims in Answer}}$ | Zero-hallucination check ensuring claims are verified in retrieved context. |
| **Citation Accuracy** | $\ge 95\%$ | $\frac{\text{Valid Citations}}{\text{Total Citations}}$ | Verifies that citations correspond to valid source chunks with exact excerpts. |

### 2. Multi-Agent Operational Metrics
| Metric | Target | Description |
|---|---|---|
| **Task Success Rate** | $\ge 95\%$ | Autonomous completion rate of multi-step workflows without unhandled exceptions. |
| **Planning Accuracy** | $\ge 90\%$ | Measures whether Planner Agent subtasks adhere to valid operational sequencing. |
| **Tool Selection Accuracy**| $\ge 95\%$ | F1 score of invoked tools vs. required tools without spurious invocations. |
| **Execution Success** | $\ge 98\%$ | Ratio of approved tool executions that complete cleanly. |
| **Failure Rate** | $\le 5\%$ | Proportion of runs that fail or require degraded fallbacks. |

---

## Security

NEXUS AI adheres to **Zero-Trust AI Design** and **Defense-in-Depth**:

```mermaid
flowchart LR
    UntrustedData["Untrusted Input / File / Output"] --> Sanitize["PromptGuard Sanitization"]
    Sanitize --> Delimiters["Structural Tag Isolation\n<SYSTEM> / <RETRIEVED_DOCUMENT> / <TOOL_OUTPUT>"]
    Delimiters --> LLM["LLM Reasoning Layer"]
    LLM --> ToolCallReq["Agent Tool Call Request"]
    
    subgraph SecurityGuard["5-Step Tool Security Guard"]
        Step1["1. User Permission Check"] --> Step2["2. Tool Scope Check"]
        Step2 --> Step3["3. Schema & Path Traversal Check"]
        Step3 --> Step4["4. Risk Assessment (Low to Critical)"]
        Step4 --> Step5{"5. High Risk?"}
    end
    
    ToolCallReq --> SecurityGuard
    Step5 -- "Yes" --> PendingProposal["Stage ActionProposal (Pending)"]
    PendingProposal --> HumanApproval{"Human Approval"}
    HumanApproval -- "Approved" --> Execution["Execute Tool"]
    HumanApproval -- "Rejected" --> Abort["Abort Execution"]
    Step5 -- "No (Read-Only)" --> Execution
    
    Execution --> AuditRedaction["Redact Secrets & Credentials"]
    AuditRedaction --> ImmutableAudit[("Immutable Audit Log")]
```

1. **AI Agents Never Act Alone**: Sensitive actions (`create_event`, `send_email`, `create_issue`, `delete_task`) cannot execute without explicit human confirmation.
2. **Prompt Injection Defense**: Third-party documents and tool outputs are treated as untrusted and wrapped in tamper-resistant structural delimiters (`<RETRIEVED_DOCUMENT>`, `<TOOL_OUTPUT>`). Delimiter breakout attempts are defanged.
3. **Hermetic Multi-Tenancy**: All database queries, vector searches, and graph traversals are scoped by authenticated `user_id`.
4. **Malicious File Ingestion Prevention**: Uploaded files undergo magic bytes inspection (PDF `%PDF-`, DOCX `PK\x03\x04`), executable headers (PE `MZ`, ELF `\x7fELF`, script shebangs `#!`) are rejected, and sizes are capped at 25MB.
5. **Credential-Sanitized Audit Trail**: Every tool invocation immutably logs user identity, parameters, and results, automatically redacting passwords, tokens, and authorization keys.

---

## Screenshots

<!-- Screenshot placeholders for portfolio and GitHub presentation -->

| Executive Dashboard | Knowledge Graph Explorer |
|:---:|:---:|
| ![Executive Dashboard](docs/screenshots/dashboard.svg)<br>*Productivity metrics, deadlines, and proactive AI recommendations* | ![Knowledge Graph](docs/screenshots/knowledge_graph.svg)<br>*Interactive force-directed entity relationship visualization* |

| Streaming Chat & Citations | AI Evaluation & Waterfall Traces |
|:---:|:---:|
| ![Streaming Chat](docs/screenshots/chat.svg)<br>*Real-time SSE token streaming with clickable citations and tool activity* | ![AI Evaluation](docs/screenshots/evaluation.svg)<br>*7-stage waterfall distributed execution tracing and RAG benchmarks* |

| Cognitive Memory Manager | Controlled Actions & Audit Log |
|:---:|:---:|
| ![Cognitive Memory](docs/screenshots/memory.svg)<br>*4-tier cognitive memory cards with importance scores and type filters* | ![Actions & Audit](docs/screenshots/actions.svg)<br>*Human-in-the-loop confirmation cards and sanitized audit log trail* |

---

## Demo

Experience the flagship workflow in the web application:

1. **Upload Context**: Navigate to the **Knowledge Vault** in the Chat page and upload a target Job Description (e.g., `Job_Description.pdf`) and your Resume (e.g., `Resume.docx`).
2. **Schedule Interview**: Add an interview event on the **Calendar** page for tomorrow (e.g., *"Interview at Stripe for Senior Cloud Engineer"*).
3. **Trigger Workflow**: In the **Chat** interface, ask:
   > *"I have an interview tomorrow. Help me prepare."*
4. **Observe Real-Time Orchestration**:
   - The SSE stream displays real-time agent activity:
     `Understanding request...` → `Finding interview...` → `Reading job description...` → `Analyzing your skills...` → `Checking relevant projects...` → `Identifying skill gaps...` → `Creating preparation plan...` → `Waiting for calendar approval...`
5. **Human-in-the-Loop Action Confirmation**:
   - An **Action Confirmation Card** appears staging calendar prep blocks:
     `Interview Preparation: SQL & System Design Blocks (Tomorrow 6:00 PM – 9:30 PM)`.
   - Click **[Approve]** to execute the calendar booking.
6. **Inspect Audit Log & Memory**:
   - View the executed action in the **Actions** page audit trail.
   - Check the **Memory** page to view the newly formed episodic memory.

---

## Future Improvements

- **More Connectors**: Native bi-directional sync with Google Workspace (Gmail, Google Calendar, Google Drive), Notion, Slack, and Jira.
- **Voice Interface**: Low-latency, speech-to-speech conversational interaction using Whisper and streaming voice models.
- **Multimodal Memory**: Ingestion, indexing, and visual recall for architectural whiteboards, screenshots, and meeting slides.
- **Advanced Autonomous Planning**: Dynamic DAG re-planning, self-correcting agent loops, and Monte Carlo tree search for strategic long-term goals.
- **Better Recommendation Models**: Offline reinforcement learning from human feedback (RLHF) to tune proactive priority scoring based on historical user acceptance patterns.

---

## Limitations

- **Local Mock Providers**: When external OAuth credentials (e.g., Google Calendar, GitHub, SMTP) are not configured, the platform falls back to simulated mock providers to guarantee offline development.
- **Local Embedding Resolution**: The built-in offline dense vectorizer uses a 384-dimensional semantic subword frequency model; while fast and zero-cost, remote models like OpenAI `text-embedding-3-small` provide higher semantic nuance for complex multi-page academic literature.
- **Single-Host Orchestration**: Agent execution is currently coordinated within the FastAPI async runtime rather than across distributed Celery worker clusters.
- **Neo4j Memory Footprint**: Running Neo4j Community via Docker requires at least 1GB of dedicated RAM; the platform automatically switches to an in-memory graph repository if Neo4j is offline.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```text
MIT License
Copyright (c) 2026 Sanjai Saravana / NEXUS AI Contributors
```

---

## 📚 Deep-Dive Documentation

For detailed architectural and implementation specifications, see the `docs/` directory:

- [System Architecture](docs/architecture.md) — Full-stack system topology, component interactions, and data flows.
- [AI Architecture](docs/ai-architecture.md) — Provider-agnostic LLMs, embeddings, multi-agent orchestrator, and prompt guards.
- [Hybrid RAG Architecture](docs/rag.md) — Chunking pipeline, dense+sparse retrieval, RRF reranking, and anti-hallucination.
- [Personalized AI Memory](docs/memory.md) — 4-tier cognitive memory architecture, noise filtering, and deduplication.
- [Knowledge Graph Architecture](docs/knowledge-graph.md) — Neo4j entity ontology, Cypher querying, and canvas explorer.
- [Multi-Agent Architecture](docs/agents.md) — Agent roles, planner decomposition, state tracking, and activity streams.
- [Tools & Secure Action Execution](docs/tools.md) — 9 tool domains, 5-step security guard, and human-in-the-loop approvals.
- [Security Architecture & Hardening](docs/security.md) — STRIDE threat modeling, prompt defense, and multi-tenant isolation.
- [AI Evaluation & Observability](docs/evaluation.md) — Quantitative RAG/agent benchmarks, waterfall tracing, and MLflow MLOps.
- [Deployment Guide](docs/deployment.md) — Docker Compose production guide, local setup, and disaster recovery.
