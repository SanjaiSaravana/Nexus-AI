# NEXUS AI — Master Documentation Index

> **Agentic Personal Intelligence & Productivity Platform**
> Version: 1.0 (Pre-Implementation Architecture)
> Date: 2026-10-07

---

## What Is NEXUS AI?

NEXUS AI is a unified personal intelligence layer that connects a person's scattered digital
information (documents, emails, calendar, tasks, notes, projects, goals, conversations, and
GitHub repositories) into a single reasoning system. It doesn't just retrieve data—it
understands relationships, remembers context, reasons about goals and priorities, creates
plans, recommends actions, and executes authorized actions through tools.

### Flagship Capability Example

```
User: "I have an interview tomorrow. Help me prepare."

NEXUS:
  1. Finds the interview event on the calendar
  2. Extracts the job description from documents / email
  3. Identifies required skills from the JD
  4. Analyses the user's resume
  5. Finds relevant personal projects
  6. Retrieves related memories and past interview notes
  7. Identifies skill gaps
  8. Generates likely interview topics
  9. Creates a personalized preparation plan
 10. Creates tasks in the task system
 11. Finds available calendar slots for practice
 12. Asks for permission to act
 13. Executes approved actions (creates events, tasks, notes)
 14. Stores episodic memory of this session
```

---

## Documentation Index

| # | Document | Description |
|---|----------|-------------|
| 01 | 01_architecture.md | System-level architecture & component map |
| 02 | 02_repository_structure.md | Full monorepo layout |
| 03 | 03_database_design.md | ER diagram & all table schemas |
| 04 | 04_ai_architecture.md | LLM orchestration, embeddings, reranking |
| 05 | 05_rag_architecture.md | Hybrid RAG pipeline end-to-end |
| 06 | 06_memory_architecture.md | Semantic, episodic, procedural & working memory |
| 07 | 07_knowledge_graph.md | Neo4j schema, entity & relationship extraction |
| 08 | 08_agent_architecture.md | Multi-agent system, each agent spec |
| 09 | 09_api_architecture.md | FastAPI routes, request/response contracts |
| 10 | 10_security.md | AuthN, AuthZ, permission layer, prompt injection protection |
| 11 | 11_deployment.md | Docker Compose, CI/CD, environments |
| 12 | 12_development_phases.md | Phased roadmap |
| 13 | 13_testing_strategy.md | Unit, integration, E2E, AI evaluation |
| 14 | 14_evaluation_strategy.md | AI-specific evaluation & observability |
| 15 | 15_phase1_checklist.md | Actionable implementation checklist |

---

## Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Primary DB | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Knowledge Graph | Neo4j 5 |
| AI / LLM | Configurable (OpenAI / Anthropic / Gemini / local via Ollama) |
| Embeddings | Configurable (OpenAI / Cohere / local) |
| Observability | Langfuse, OpenTelemetry |
| MLOps | MLflow |
| DevOps | Docker, Docker Compose, GitHub Actions |

---

## Core Design Principles

1. **Privacy-first** — all data stays in user-controlled infrastructure by default
2. **Configurable AI** — swap LLM / embedding providers without code changes
3. **Permission-gated actions** — no external action executes without explicit user approval
4. **Explainability** — every recommendation cites its source (document, memory, entity)
5. **Observability** — every AI call is traced, evaluated, and logged
6. **Modularity** — agents, tools, and memory systems are independently deployable
7. **Graceful degradation** — system degrades to read-only intelligence if action services fail
