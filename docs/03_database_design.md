# 03 — Database Design

## ER Diagram

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK
        string username
        string hashed_password
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
    }

    PROFILES {
        uuid id PK
        uuid user_id FK
        string full_name
        string bio
        json preferences
        json integrations
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        string title
        string source_type
        string source_url
        string file_path
        string mime_type
        bigint file_size
        string status
        json metadata
        timestamp ingested_at
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        integer chunk_index
        text content
        vector embedding
        json metadata
        integer token_count
        timestamp created_at
    }

    PROJECTS {
        uuid id PK
        uuid user_id FK
        string name
        text description
        string status
        date start_date
        date end_date
        json metadata
        timestamp created_at
        timestamp updated_at
    }

    TASKS {
        uuid id PK
        uuid user_id FK
        uuid project_id FK
        uuid parent_task_id FK
        string title
        text description
        string status
        string priority
        date due_date
        json metadata
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
    }

    GOALS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string category
        string status
        integer progress_pct
        date target_date
        json success_criteria
        timestamp created_at
        timestamp updated_at
    }

    EVENTS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string event_type
        timestamp start_time
        timestamp end_time
        string location
        string external_id
        string external_source
        json attendees
        json metadata
        timestamp created_at
        timestamp updated_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string title
        string status
        json context_snapshot
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        string role
        text content
        json citations
        json tool_calls_used
        integer token_count
        json metadata
        timestamp created_at
    }

    MEMORIES {
        uuid id PK
        uuid user_id FK
        string memory_type
        text content
        vector embedding
        float importance_score
        integer access_count
        json source_references
        json entities
        timestamp last_accessed_at
        timestamp expires_at
        timestamp created_at
        timestamp updated_at
    }

    AGENT_RUNS {
        uuid id PK
        uuid user_id FK
        uuid conversation_id FK
        string agent_type
        string status
        json input
        json output
        json plan
        integer total_tokens
        float total_cost_usd
        float duration_seconds
        string langfuse_trace_id
        timestamp created_at
        timestamp completed_at
    }

    AGENT_STEPS {
        uuid id PK
        uuid agent_run_id FK
        integer step_index
        string step_type
        string agent_type
        json input
        json output
        string status
        float duration_seconds
        timestamp created_at
    }

    TOOL_CALLS {
        uuid id PK
        uuid agent_run_id FK
        uuid agent_step_id FK
        string tool_name
        json input
        json output
        boolean success
        string error_message
        float duration_seconds
        boolean required_permission
        boolean permission_granted
        timestamp created_at
    }

    PERMISSIONS {
        uuid id PK
        uuid user_id FK
        string permission_type
        string resource_type
        json scope
        boolean is_active
        timestamp expires_at
        timestamp created_at
        timestamp updated_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string action_type
        string resource_type
        uuid resource_id
        json before_state
        json after_state
        string ip_address
        string user_agent
        boolean success
        string error_message
        timestamp created_at
    }

    EVALUATIONS {
        uuid id PK
        uuid agent_run_id FK
        string eval_type
        float score
        json criteria_scores
        string judge_model
        json judge_reasoning
        string dataset_name
        timestamp created_at
    }

    USERS ||--|| PROFILES : "has"
    USERS ||--o{ DOCUMENTS : "owns"
    USERS ||--o{ PROJECTS : "owns"
    USERS ||--o{ TASKS : "owns"
    USERS ||--o{ GOALS : "owns"
    USERS ||--o{ EVENTS : "owns"
    USERS ||--o{ CONVERSATIONS : "has"
    USERS ||--o{ MEMORIES : "has"
    USERS ||--o{ AGENT_RUNS : "triggers"
    USERS ||--o{ PERMISSIONS : "has"
    USERS ||--o{ AUDIT_LOGS : "generates"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "split into"
    PROJECTS ||--o{ TASKS : "contains"
    TASKS ||--o{ TASKS : "subtask of"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    CONVERSATIONS ||--o{ AGENT_RUNS : "triggers"
    AGENT_RUNS ||--o{ AGENT_STEPS : "has"
    AGENT_RUNS ||--o{ EVALUATIONS : "evaluated by"
    AGENT_STEPS ||--o{ TOOL_CALLS : "makes"
```

---

## Table Schemas (Detailed)

### `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login identifier |
| username | VARCHAR(50) | UNIQUE | Display name |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt hash |
| is_active | BOOLEAN | DEFAULT TRUE | Account enabled |
| is_verified | BOOLEAN | DEFAULT FALSE | Email verified |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | | Updated via trigger |

### `document_chunks`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| document_id | UUID | FK → documents.id, ON DELETE CASCADE | |
| chunk_index | INTEGER | NOT NULL | Position in document |
| content | TEXT | NOT NULL | Raw chunk text |
| embedding | VECTOR(1536) | | pgvector column |
| metadata | JSONB | | page, section, etc. |
| token_count | INTEGER | | Approx tokens |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes:**
```sql
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX ON document_chunks (document_id);
CREATE INDEX ON document_chunks USING gin (metadata);
```

### `memories`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id | |
| memory_type | VARCHAR(50) | CHECK IN ('semantic','episodic','procedural','working') | |
| content | TEXT | NOT NULL | |
| embedding | VECTOR(1536) | | For similarity search |
| importance_score | FLOAT | DEFAULT 0.5 | 0–1 scale |
| access_count | INTEGER | DEFAULT 0 | Used for decay |
| source_references | JSONB | | Links to documents, events |
| entities | JSONB | | Extracted named entities |
| last_accessed_at | TIMESTAMPTZ | | For LRU decay |
| expires_at | TIMESTAMPTZ | | NULL = permanent |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | | |

**Indexes:**
```sql
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX ON memories (user_id, memory_type);
CREATE INDEX ON memories (importance_score DESC);
CREATE INDEX ON memories (expires_at) WHERE expires_at IS NOT NULL;
```

### `agent_runs`
Full record of every AI orchestration session for observability, debugging, and billing.

### `audit_logs`
Immutable append-only log of all state-changing operations. Critical for security and compliance.

---

## PostgreSQL Extensions Required

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- fuzzy text search (BM25 partial)
CREATE EXTENSION IF NOT EXISTS "btree_gin";    -- Composite GIN indexes
```

---

## Data Retention Policy

| Table | Retention | Policy |
|-------|-----------|--------|
| audit_logs | 7 years | Immutable, partitioned by year |
| agent_runs | 1 year | Compressed after 90 days |
| agent_steps | 90 days | Linked to agent_runs |
| working memory | Session | Expires on conversation close |
| episodic memory | 2 years | Decay via importance_score |
| tool_calls | 90 days | |
| messages | Indefinite | User-controlled deletion |
