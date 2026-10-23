# 01 — System Architecture

## High-Level Architecture

```mermaid
graph TD
    subgraph Client["Frontend (React + TypeScript + Vite)"]
        UI[Chat UI]
        Dashboard[Dashboard]
        DocViewer[Document Viewer]
        KGViewer[Knowledge Graph Viewer]
        Settings[Settings / Permissions]
    end

    subgraph Gateway["API Gateway Layer"]
        APIGW[FastAPI — REST + WebSocket]
        Auth[Auth Middleware — JWT / OAuth2]
        RateLimit[Rate Limiter]
    end

    subgraph Orchestration["AI Orchestration Layer"]
        Orchestrator[AI Orchestrator]
        IntentDetect[Intent Detector]
        CtxBuilder[Context Builder]
        Planner[Planning Engine]
        PermLayer[Permission & Approval Layer]
    end

    subgraph Agents["Multi-Agent System"]
        PlannerAgent[Planner Agent]
        ResearchAgent[Research Agent]
        MemoryAgent[Memory Agent]
        ProjectAgent[Project Agent]
        TaskAgent[Task Agent]
        CalAgent[Calendar Agent]
        ExecAgent[Execution Agent]
    end

    subgraph Intelligence["Intelligence Layer"]
        RAG[Hybrid RAG Engine]
        Reranker[Reranker]
        MemoryEngine[Memory Engine]
        KGEngine[Knowledge Graph Engine]
        RecEngine[Recommendation Engine]
        ProactiveEngine[Proactive Intelligence]
    end

    subgraph Storage["Storage Layer"]
        PG[(PostgreSQL + pgvector)]
        Redis[(Redis Cache)]
        Neo4j[(Neo4j KG)]
        FileStore[(Object Storage)]
    end

    subgraph Tools["Tool Layer"]
        DocTool[Document Tool]
        CalTool[Calendar Tool]
        TaskTool[Task Tool]
        EmailTool[Email Tool]
        GitHubTool[GitHub Tool]
        WebTool[Web Search Tool]
        CodeTool[Code Execution Tool]
    end

    subgraph Observability["Observability Layer"]
        Langfuse[Langfuse Tracing]
        OTEL[OpenTelemetry]
        MLflow[MLflow Experiments]
    end

    UI --> APIGW
    Dashboard --> APIGW
    DocViewer --> APIGW
    KGViewer --> APIGW
    Settings --> APIGW

    APIGW --> Auth
    Auth --> RateLimit
    RateLimit --> Orchestrator

    Orchestrator --> IntentDetect
    IntentDetect --> CtxBuilder
    CtxBuilder --> Planner
    Planner --> PlannerAgent
    Planner --> ResearchAgent
    Planner --> MemoryAgent

    PlannerAgent --> ProjectAgent
    PlannerAgent --> TaskAgent
    PlannerAgent --> CalAgent
    PlannerAgent --> ExecAgent

    ResearchAgent --> RAG
    MemoryAgent --> MemoryEngine
    ProjectAgent --> RAG
    TaskAgent --> Tools
    CalAgent --> Tools
    ExecAgent --> PermLayer

    RAG --> PG
    RAG --> Reranker
    MemoryEngine --> PG
    MemoryEngine --> Redis
    KGEngine --> Neo4j

    PermLayer --> Tools

    Orchestrator --> Langfuse
    Orchestrator --> OTEL
    Orchestrator --> MLflow
```

---

## Layer Descriptions

### 1. Frontend Layer
- **Chat UI**: Conversational interface, streaming responses, citation display
- **Dashboard**: Goals, tasks, calendar, project overview with AI insights
- **Document Viewer**: Upload, view, annotated documents with AI summaries
- **Knowledge Graph Viewer**: Interactive graph visualization of entities/relationships
- **Settings / Permissions**: Manage integrations, data access, and action approvals

### 2. API Gateway Layer
- FastAPI with async handlers and WebSocket for streaming
- JWT-based authentication with OAuth2 for external integrations
- Request validation via Pydantic models
- Rate limiting per user and per endpoint

### 3. AI Orchestration Layer
- **AI Orchestrator**: Coordinates all AI components for a given user request
- **Intent Detector**: Classifies user intent (query, action, planning, reflection)
- **Context Builder**: Assembles relevant context from memory, KG, and RAG
- **Planning Engine**: Decomposes complex requests into agent task graphs
- **Permission Layer**: Requires explicit approval before mutating external state

### 4. Multi-Agent System
Seven specialized agents operate as a directed graph orchestrated by the Planner Agent.

### 5. Intelligence Layer
- **Hybrid RAG**: BM25 + dense vector retrieval with reranking
- **Memory Engine**: Manages 4 types of memory with selective consolidation
- **Knowledge Graph Engine**: Entity/relationship extraction and graph traversal
- **Recommendation Engine**: Surfaces proactive suggestions based on context
- **Proactive Intelligence**: Background monitoring and unprompted nudges

### 6. Storage Layer
| Store | Purpose |
|-------|---------|
| PostgreSQL | Relational data, document chunks, vector embeddings (pgvector) |
| Redis | Working memory, session cache, rate limiting, pub/sub |
| Neo4j | Knowledge graph — entities, relationships, traversal |
| Object Storage | Raw document files (local FS or S3-compatible) |

### 7. Tool Layer
Tools are callable functions with structured inputs/outputs, always permission-checked.

### 8. Observability Layer
- **Langfuse**: Full LLM call tracing, prompt versioning, cost tracking
- **OpenTelemetry**: Distributed traces across all services
- **MLflow**: Experiment tracking for model evaluation and fine-tuning

---

## Data Flow — Query Request

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant ORCH as Orchestrator
    participant INTENT as Intent Detector
    participant CTX as Context Builder
    participant PLAN as Planner Agent
    participant MEM as Memory Agent
    participant RAG as RAG Engine
    participant LLM as LLM Provider
    participant LANG as Langfuse

    U->>FE: "Help me prepare for tomorrow's interview"
    FE->>API: POST /api/v1/chat/message
    API->>ORCH: dispatch(message, user_context)
    ORCH->>INTENT: classify_intent(message)
    INTENT-->>ORCH: {type: "complex_planning", confidence: 0.95}
    ORCH->>CTX: build_context(user_id, intent)
    CTX->>MEM: retrieve_relevant_memories(query)
    CTX->>RAG: retrieve_chunks(query)
    MEM-->>CTX: [memory_results]
    RAG-->>CTX: [chunk_results + citations]
    CTX-->>ORCH: assembled_context
    ORCH->>PLAN: execute(intent, context)
    PLAN->>LLM: generate_plan(prompt + context)
    LLM-->>PLAN: plan_with_sub_tasks
    PLAN-->>ORCH: agent_task_graph
    ORCH-->>FE: streaming_response (SSE)
    ORCH->>LANG: trace(session_id, all_calls)
```

---

## Data Flow — Action Request (Permission-Gated)

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant ORCH as Orchestrator
    participant EXEC as Execution Agent
    participant PERM as Permission Layer
    participant TOOL as Tool
    participant AUDIT as Audit Log

    ORCH->>EXEC: proposed_actions[create_task, create_event]
    EXEC->>PERM: request_approval(actions)
    PERM-->>FE: approval_required(action_summary)
    FE-->>U: "May I create 3 tasks and 1 calendar event?"
    U->>FE: approve / reject / modify
    FE->>PERM: user_decision
    PERM->>EXEC: approved_actions
    EXEC->>TOOL: execute(action)
    TOOL-->>EXEC: result
    EXEC->>AUDIT: log(user_id, action, result, timestamp)
    EXEC-->>ORCH: execution_result
```

---

## Cross-Cutting Concerns

| Concern | Implementation |
|---------|---------------|
| Prompt Injection | Input sanitization + system prompt hardening + output validation |
| PII Protection | Data classification at ingest + field-level encryption |
| Multi-tenancy | Row-level security in PostgreSQL, namespace isolation in Neo4j |
| Idempotency | Action IDs with deduplication keys |
| Retry Logic | Exponential backoff on LLM and tool calls |
| Circuit Breakers | Per-integration circuit breakers to prevent cascade failures |
